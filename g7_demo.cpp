#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <d3dcompiler.h>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <atomic>
#include <string>
#include <cstdint>
#include <cerrno>
#include <limits>
#include <cmath>
#include <stdexcept>
#include <utility>
#include "g7_native.h"
#include "g7_scene.h"
#include "third_party/imgui/imgui.h"
#include "third_party/imgui/backends/imgui_impl_win32.h"
#include "third_party/imgui/backends/imgui_impl_dx12.h"
#ifndef G7_REVISION
#define G7_REVISION "unavailable"
#endif
extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND,UINT,WPARAM,LPARAM);
template<class T> static void drop(T*&p){if(p){p->Release();p=nullptr;}}
static void check(HRESULT h){if(FAILED(h)){char b[100];snprintf(b,sizeof(b),"D3D12 operation failed: 0x%08lx",(unsigned long)h);throw std::runtime_error(b);}}
static double now(){LARGE_INTEGER q,f;QueryPerformanceCounter(&q);QueryPerformanceFrequency(&f);return double(q.QuadPart)/f.QuadPart;}
// All runtime assets and evidence belong to this checkout, regardless of the
// shell/shortcut working directory. The supported executable lives in zig-out/bin.
static void projectDirectory(){
 wchar_t module[32768];DWORD length=GetModuleFileNameW(nullptr,module,32768);
 if(!length||length>=32768)throw std::runtime_error("Cannot resolve SunderG7 executable location");
 std::wstring directory(module,length);auto slash=directory.find_last_of(L"\\/");
 if(slash==std::wstring::npos)throw std::runtime_error("Cannot resolve SunderG7 executable directory");
 directory.resize(slash);directory+=L"\\..\\..";
 if(!SetCurrentDirectoryW(directory.c_str()))throw std::runtime_error("Cannot open Sunder project directory relative to zig-out/bin/SunderG7.exe");
 const char *entries[]={"clear","prepare","hash","contacts","solve","gather","integrate","validate","publish","converge_clear","converge_check","converge_finish","cache_clear","cache_publish","color","colored_solve","color_prepare"};
 for(auto entry:entries){char path[128];snprintf(path,sizeof(path),"evidence/p10/build/p3_%s.dxil",entry);DWORD attr=GetFileAttributesA(path);if(attr==INVALID_FILE_ATTRIBUTES||(attr&FILE_ATTRIBUTE_DIRECTORY))throw std::runtime_error(std::string("Missing Physics3 shader: ")+path+". Run LAUNCH_G7_CAPABILITIES_DEMO.cmd to build project assets.");}
 for(auto path:{"zig-out/bin/g7_sphere_vs.dxil","zig-out/bin/g7_sphere_ps.dxil","zig-out/bin/g7_container_vs.dxil","zig-out/bin/g7_container_ps.dxil"}){DWORD attr=GetFileAttributesA(path);if(attr==INVALID_FILE_ATTRIBUTES||(attr&FILE_ATTRIBUTE_DIRECTORY))throw std::runtime_error(std::string("Missing rendering shader: ")+path+". Run LAUNCH_G7_CAPABILITIES_DEMO.cmd to build project assets.");}
}
struct Simulation {
 Physics3 *p=nullptr;SRWLOCK lock=SRWLOCK_INIT,requestLock=SRWLOCK_INIT;
 std::atomic<bool> sample{false},stop{false},paused{false},reset{false},single{false};std::atomic<float> speed{1};
 G7Config config,requested;G7Scene scene;unsigned active=0,spawned=0,accepted=0,rejected=0,epoch=0;bool moving=false,fault=false;double nextSpawn=0;
 Ph3Result result={};Ph3Validation validation={};double cpuUs=0,hostUs=0,tps=0;unsigned geometric=0,cross=0,island=0,sampleTick=0;char error[256]={};HANDLE thread=nullptr;FILE *log=nullptr;
 void init(){config.validate();p=ph3_open(uint32_t(config.count),config.contacts(),config.iterations,0,"evidence/p10/build");if(!p)throw std::runtime_error("Physics3 device/admission failed: check GPU memory budget and requested body/contact capacities");static std::atomic<unsigned> serial{0};char path[512];SYSTEMTIME time;GetSystemTime(&time);snprintf(path,sizeof(path),"evidence/g7/native-showcase/session-%04u%02u%02u-%02u%02u%02u-%lu-%u.jsonl",time.wYear,time.wMonth,time.wDay,time.wHour,time.wMinute,time.wSecond,(unsigned long)GetCurrentProcessId(),serial++);log=fopen(path,"w");restart();}
 void restart(){
  config.validate();if(scene.capacity&&scene.capacity!=config.count)throw std::runtime_error("Body capacity change requires a full native renderer/context rebuild");scene.generate(config);auto s=scene.initial(0,false);auto planes=scene.planes(config.scene);
  // All tracked consumer fences must finish before replacing a scene.
  bool seeded=false;for(int i=0;i<100&&!seeded;i++){seeded=ph3_seed(p,s.data(),planes.data(),unsigned(planes.size()/4))!=0;if(!seeded)Sleep(1);}
  if(!seeded)throw std::runtime_error("Reset blocked by GPU lease/device; last accepted display retained");
  active=spawned=accepted=rejected=0;moving=config.scene==2;nextSpawn=0;fault=false;error[0]=0;result={};validation={};geometric=cross=island=sampleTick=0;epoch++;
 }
 void tick(){
  unsigned next=active;bool activate=false;
  if(active<unsigned(config.count)&&(config.scene!=2||accepted/128.>=nextSpawn)){next=std::min(unsigned(config.count),active+config.batch);auto s=scene.initial(next,config.scene==2);if(!(config.scene==2?ph3_stage_append(p,s.data(),active,next):ph3_stage(p,s.data())))throw std::runtime_error("Spawn stage failed");spawned=next;nextSpawn=accepted/128.+1/config.spawnHz;}
  else if(active==unsigned(config.count)&&!moving){auto s=scene.initial(active,true);if(!ph3_stage(p,s.data()))throw std::runtime_error("Activation stage failed");activate=true;}
  float gravity[3]={config.gravityX,config.gravityY,moving?config.gravity:0};FILETIME ct,et,k0,u0,k1,u1;GetThreadTimes(GetCurrentThread(),&ct,&et,&k0,&u0);double begin=now();
  if(!ph3_tick(p,1.f/128,gravity,(config.cell>0?config.cell:(config.scene==2?2.5f:1.f)),0,&result))throw std::runtime_error("Native host/device tick failed");
  hostUs=(now()-begin)*1e6;GetThreadTimes(GetCurrentThread(),&ct,&et,&k1,&u1);auto ft=[](FILETIME f){return (uint64_t(f.dwHighDateTime)<<32)|f.dwLowDateTime;};cpuUs=double(ft(k1)+ft(u1)-ft(k0)-ft(u0))*.1;ph3_validation(p,&validation);
  if(result.error){rejected++;fault=true;paused=true;ph3_drop_stage(p);snprintf(error,sizeof(error),"GPU rejected candidate: flags %u",result.error);}
  else {active=next;accepted++;if(activate)moving=true;}
  if(log){fprintf(log,"{\"epoch\":%u,\"scene\":%d,\"requested\":%llu,\"active\":%u,\"accepted\":%u,\"rejected\":%u,\"global_tick\":%u,\"published_slots\":%u,\"flags\":%u,\"constraints\":%u,\"candidates\":%u,\"max_degree\":%u,\"gpu_us\":%.3f,\"host_us\":%.3f,\"physics_committed\":%llu}\n",epoch,config.scene,(unsigned long long)config.count,active,accepted,rejected,result.tick,result.published,result.error,result.contacts,result.candidates,result.max_degree,result.phases_us[7],hostUs,(unsigned long long)result.committed);fflush(log);}
 }
 void sampleContacts(){
  if(!accepted||result.error||!active)return;
  std::vector<unsigned char> raw(size_t(128)*result.contacts);if(result.contacts&&!ph3_contacts(p,raw.data(),result.contacts))throw std::runtime_error("Contact diagnostic readback failed");
  std::vector<unsigned> parent(active),sizes(active,1);for(unsigned i=0;i<active;i++)parent[i]=i;
  auto root=[&](unsigned i){while(parent[i]!=i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  geometric=cross=0;island=1;
  for(unsigned k=0;k<result.contacts;k++){unsigned a,b;double gap;auto r=raw.data()+128*k;memcpy(&a,r,4);memcpy(&b,r+4,4);memcpy(&gap,r+80,8);if(a>=active||b>=active||gap>0)continue;geometric++;cross+=scene.authored[size_t(38)*scene.capacity+a]!=scene.authored[size_t(38)*scene.capacity+b];unsigned x=root(a),y=root(b);if(x!=y){parent[y]=x;sizes[x]+=sizes[y];island=std::max(island,sizes[x]);}}
  sampleTick=result.tick;
 }
 static DWORD WINAPI run(void *arg){auto&s=*(Simulation*)arg;double due=now(),start=now();unsigned ticks=0;HANDLE timer=CreateWaitableTimerExW(nullptr,nullptr,2,TIMER_ALL_ACCESS);if(!timer)timer=CreateWaitableTimerW(nullptr,FALSE,nullptr);
  while(!s.stop){
   if(s.sample.exchange(false)){AcquireSRWLockExclusive(&s.lock);try{s.sampleContacts();}catch(const std::exception&e){snprintf(s.error,sizeof(s.error),"%s",e.what());}ReleaseSRWLockExclusive(&s.lock);}
   if(s.reset.exchange(false)){AcquireSRWLockExclusive(&s.lock);try{AcquireSRWLockShared(&s.requestLock);s.config=s.requested;ReleaseSRWLockShared(&s.requestLock);s.restart();s.paused=false;}catch(const std::exception&e){s.fault=true;s.paused=true;snprintf(s.error,sizeof(s.error),"%s",e.what());}ReleaseSRWLockExclusive(&s.lock);due=now();}
   bool step=s.single.exchange(false);double t=now();
   if(!s.fault&&((!s.paused&&t>=due)||step)){
    AcquireSRWLockExclusive(&s.lock);try{s.tick();ticks++;}catch(const std::exception&e){s.fault=true;s.paused=true;snprintf(s.error,sizeof(s.error),"%s",e.what());}if(now()-start>=.5){s.tps=ticks/(now()-start);ticks=0;start=now();}ReleaseSRWLockExclusive(&s.lock);
    double interval=s.config.scene!=2&&s.active<unsigned(s.config.count)?1/s.config.spawnHz:(1./128)/s.speed.load();due=std::max(due+interval,t);
   }
   double remaining=due-now();if(s.paused||s.fault)Sleep(2);else if(remaining>0&&timer){LARGE_INTEGER duration;duration.QuadPart=-std::max<LONGLONG>(1,LONGLONG(remaining*1e7));SetWaitableTimer(timer,&duration,0,nullptr,nullptr,FALSE);WaitForSingleObject(timer,20);}else SwitchToThread();
  }if(timer)CloseHandle(timer);return 0;
 }
 void close(){stop=true;if(thread){WaitForSingleObject(thread,INFINITE);CloseHandle(thread);thread=nullptr;}if(log){fclose(log);log=nullptr;}if(p&&!ph3_close(p))fprintf(stderr,"Physics close failed: outstanding lease/device\n");p=nullptr;}
};
struct Camera {float yaw=.7f,pitch=.42f,distance=24,target[3]={};void reset(float extent,unsigned scene=0){yaw=scene==2?.10f:.7f;pitch=scene==2?.38f:.42f;distance=scene==2?58.f:extent*3.8f;target[0]=scene==2?-6.f:0;target[1]=0;target[2]=scene==2?6.f:0;}};
struct Constants {float eye[4],right[4],up[4],forward[4],lens[4];unsigned population,stride,scene,quality,previousPopulation;float alpha;unsigned padding[2];};
struct Renderer {
 HWND window=nullptr;Simulation *sim=nullptr;ID3D12Device *device=nullptr;ID3D12CommandQueue *queue=nullptr;IDXGISwapChain3 *swap=nullptr;
 ID3D12DescriptorHeap *rtv=nullptr,*dsv=nullptr,*gui=nullptr;ID3D12Resource *backs[3]={},*depth=nullptr,*snapshot=nullptr,*previousSnapshot=nullptr,*timestampRead=nullptr;
 ID3D12CommandAllocator *allocator=nullptr;ID3D12GraphicsCommandList *list=nullptr;ID3D12Fence *fence=nullptr;ID3D12RootSignature *root=nullptr;ID3D12PipelineState *pipeline=nullptr,*containerPipeline=nullptr;ID3D12QueryHeap *queries=nullptr;
 char driver[64]={};UINT64 renderCommitted=0;HANDLE event=nullptr;UINT stride=0,width=0,height=0;UINT64 serial=0,frequency=0,lastTimedSerial=0;bool smooth=true;unsigned previousPopulation=0;double copyTime=0,copyInterval=1./60;bool unfenced=false,snapshotRead=false,hud=true,fullscreen=false,quit=false,quality=true,follow=false,reconfigure=false;RECT restored={};Camera camera;
 double gpuSum=0;uint64_t gpuSampleCount=0,renderedFrames=0;unsigned minPopulation=UINT_MAX,maxPopulation=0;unsigned copiedFrames=0;uint64_t displayRequested=512;unsigned displaySeed=7,rejectedBodies=0;unsigned displayActive=0,displayEpoch=0,displayScene=0,displayGeneration=0;double gpuUs=0,fps=0;Ph3Result stats={};Ph3Validation validation={};unsigned accepted=0,rejected=0;double cpuUs=0,hostUs=0,tps=0;unsigned geometric=0,cross=0,island=0,sampleTick=0;std::string error,admissionError;G7Config edit;float displayExtent=6;
 D3D12_CPU_DESCRIPTOR_HANDLE target(unsigned i){auto h=rtv->GetCPUDescriptorHandleForHeapStart();h.ptr+=i*stride;return h;}
 void barrier(ID3D12Resource*r,D3D12_RESOURCE_STATES a,D3D12_RESOURCE_STATES b){D3D12_RESOURCE_BARRIER t={};t.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;t.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,a,b};list->ResourceBarrier(1,&t);}
 void wait(){if(serial&&fence->GetCompletedValue()<serial){if(fence->GetCompletedValue()==UINT64_MAX)throw std::runtime_error("Render device removed");check(fence->SetEventOnCompletion(serial,event));while(WaitForSingleObject(event,10)==WAIT_TIMEOUT){MSG m;while(PeekMessageW(&m,nullptr,0,0,PM_REMOVE)){TranslateMessage(&m);DispatchMessageW(&m);}if(FAILED(device->GetDeviceRemovedReason()))throw std::runtime_error("Render device lost while awaiting fence");}}}
 ID3D12Resource *buffer(UINT64 size,D3D12_HEAP_TYPE heap){D3D12_HEAP_PROPERTIES hp={};hp.Type=heap;D3D12_RESOURCE_DESC d={};d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;d.Width=size;d.Height=d.DepthOrArraySize=d.MipLevels=1;d.SampleDesc.Count=1;d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;ID3D12Resource*r=nullptr;check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&d,heap==D3D12_HEAP_TYPE_READBACK?D3D12_RESOURCE_STATE_COPY_DEST:D3D12_RESOURCE_STATE_COMMON,nullptr,IID_PPV_ARGS(&r)));return r;}
 void resize(UINT w,UINT h){if(!w||!h)return;wait();for(auto &b:backs)drop(b);drop(depth);if(width)check(swap->ResizeBuffers(3,w,h,DXGI_FORMAT_B8G8R8A8_UNORM,0));width=w;height=h;for(unsigned i=0;i<3;i++){check(swap->GetBuffer(i,IID_PPV_ARGS(&backs[i])));device->CreateRenderTargetView(backs[i],nullptr,target(i));}
  D3D12_HEAP_PROPERTIES hp={};hp.Type=D3D12_HEAP_TYPE_DEFAULT;D3D12_RESOURCE_DESC d={};d.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;d.Width=w;d.Height=h;d.DepthOrArraySize=d.MipLevels=1;d.Format=DXGI_FORMAT_D32_FLOAT;d.SampleDesc.Count=1;d.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;D3D12_CLEAR_VALUE cv={};cv.Format=d.Format;cv.DepthStencil.Depth=1;check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&d,D3D12_RESOURCE_STATE_DEPTH_WRITE,&cv,IID_PPV_ARGS(&depth)));device->CreateDepthStencilView(depth,nullptr,dsv->GetCPUDescriptorHandleForHeapStart());renderCommitted=0;ID3D12Resource *owned[]={backs[0],backs[1],backs[2],depth,snapshot,previousSnapshot,timestampRead};for(auto r:owned){auto desc=r->GetDesc();renderCommitted+=device->GetResourceAllocationInfo(0,1,&desc).SizeInBytes;}}
 void init(HWND w,Simulation&s){window=w;sim=&s;edit=s.config;device=(ID3D12Device*)ph3_native_device(s.p);if(!device)throw std::runtime_error("No native device");device->AddRef();D3D12_COMMAND_QUEUE_DESC q={};q.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;check(device->CreateCommandQueue(&q,IID_PPV_ARGS(&queue)));check(queue->GetTimestampFrequency(&frequency));
  IDXGIFactory4 *factory=nullptr;IDXGISwapChain1 *sc=nullptr;check(CreateDXGIFactory2(0,IID_PPV_ARGS(&factory)));DXGI_SWAP_CHAIN_DESC1 d={};d.Width=1600;d.Height=900;d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.SampleDesc.Count=1;d.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;d.BufferCount=3;d.SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD;check(factory->CreateSwapChainForHwnd(queue,w,&d,nullptr,nullptr,&sc));check(sc->QueryInterface(IID_PPV_ARGS(&swap)));factory->MakeWindowAssociation(w,DXGI_MWA_NO_ALT_ENTER);IDXGIAdapter1 *adapter=nullptr;if(SUCCEEDED(factory->EnumAdapterByLuid(device->GetAdapterLuid(),IID_PPV_ARGS(&adapter)))){LARGE_INTEGER version={};if(SUCCEEDED(adapter->CheckInterfaceSupport(__uuidof(IDXGIDevice),&version)))snprintf(driver,sizeof(driver),"%u.%u.%u.%u",HIWORD(version.HighPart),LOWORD(version.HighPart),HIWORD(version.LowPart),LOWORD(version.LowPart));drop(adapter);}drop(sc);drop(factory);
  D3D12_DESCRIPTOR_HEAP_DESC hd={};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV;hd.NumDescriptors=3;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&rtv)));stride=device->GetDescriptorHandleIncrementSize(hd.Type);hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;hd.NumDescriptors=1;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&dsv)));hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;hd.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&gui)));
  check(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)));check(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator,nullptr,IID_PPV_ARGS(&list)));check(list->Close());check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));event=CreateEventW(nullptr,FALSE,FALSE,nullptr);
  snapshot=buffer(192ull*s.scene.capacity,D3D12_HEAP_TYPE_DEFAULT);previousSnapshot=buffer(192ull*s.scene.capacity,D3D12_HEAP_TYPE_DEFAULT);timestampRead=buffer(16,D3D12_HEAP_TYPE_READBACK);D3D12_QUERY_HEAP_DESC query={D3D12_QUERY_HEAP_TYPE_TIMESTAMP,2,0};check(device->CreateQueryHeap(&query,IID_PPV_ARGS(&queries)));
  D3D12_ROOT_PARAMETER rp[3]={};rp[0].ParameterType=D3D12_ROOT_PARAMETER_TYPE_SRV;rp[0].ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;rp[1].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;rp[1].Constants.Num32BitValues=sizeof(Constants)/4;
  rp[2].ParameterType=D3D12_ROOT_PARAMETER_TYPE_SRV;rp[2].Descriptor.ShaderRegister=1;rp[2].ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;D3D12_ROOT_SIGNATURE_DESC rd={3,rp,0,nullptr,D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT};ID3DBlob *blob=nullptr,*err=nullptr;check(D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&blob,&err));drop(err);check(device->CreateRootSignature(0,blob->GetBufferPointer(),blob->GetBufferSize(),IID_PPV_ARGS(&root)));drop(blob);
  auto shader=[](const wchar_t*path){ID3DBlob *b=nullptr;check(D3DReadFileToBlob(path,&b));return b;};auto vs=shader(L"zig-out/bin/g7_sphere_vs.dxil"),ps=shader(L"zig-out/bin/g7_sphere_ps.dxil");D3D12_GRAPHICS_PIPELINE_STATE_DESC pd={};pd.pRootSignature=root;pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};pd.PS={ps->GetBufferPointer(),ps->GetBufferSize()};pd.BlendState.RenderTarget[0].RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;pd.SampleMask=UINT_MAX;pd.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;pd.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;pd.RasterizerState.DepthClipEnable=TRUE;pd.DepthStencilState.DepthEnable=TRUE;pd.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;pd.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;pd.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;pd.NumRenderTargets=1;pd.RTVFormats[0]=DXGI_FORMAT_B8G8R8A8_UNORM;pd.DSVFormat=DXGI_FORMAT_D32_FLOAT;pd.SampleDesc.Count=1;check(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&pipeline)));drop(vs);drop(ps);vs=shader(L"zig-out/bin/g7_container_vs.dxil");ps=shader(L"zig-out/bin/g7_container_ps.dxil");pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};pd.PS={ps->GetBufferPointer(),ps->GetBufferSize()};check(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&containerPipeline)));drop(vs);drop(ps);
  ImGui::CreateContext();ImGui::GetIO().IniFilename=nullptr;ImGui::StyleColorsDark();auto &style=ImGui::GetStyle();style.WindowRounding=10;style.FrameRounding=5;style.WindowPadding={18,18};style.ItemSpacing={10,8};style.Colors[ImGuiCol_WindowBg]={.035f,.05f,.065f,.96f};style.Colors[ImGuiCol_Button]={.07f,.25f,.29f,1};
  char font[MAX_PATH];GetWindowsDirectoryA(font,MAX_PATH);strcat_s(font,"\\Fonts\\segoeui.ttf");ImGui::GetIO().Fonts->AddFontFromFileTTF(font,17);
  if(!ImGui_ImplWin32_Init(w)||!ImGui_ImplDX12_Init(device,1,DXGI_FORMAT_B8G8R8A8_UNORM,gui,gui->GetCPUDescriptorHandleForHeapStart(),gui->GetGPUDescriptorHandleForHeapStart()))throw std::runtime_error("ImGui initialization failed");resize(1600,900);camera.reset(s.scene.extent,s.config.scene);
 }
 void toggleFullscreen(){fullscreen=!fullscreen;if(fullscreen){GetWindowRect(window,&restored);SetWindowLongPtrW(window,GWL_STYLE,WS_POPUP|WS_VISIBLE);MONITORINFO mi={sizeof(mi)};GetMonitorInfoW(MonitorFromWindow(window,MONITOR_DEFAULTTONEAREST),&mi);SetWindowPos(window,HWND_TOP,mi.rcMonitor.left,mi.rcMonitor.top,mi.rcMonitor.right-mi.rcMonitor.left,mi.rcMonitor.bottom-mi.rcMonitor.top,SWP_FRAMECHANGED);}else{SetWindowLongPtrW(window,GWL_STYLE,WS_OVERLAPPEDWINDOW|WS_VISIBLE);SetWindowPos(window,nullptr,restored.left,restored.top,restored.right-restored.left,restored.bottom-restored.top,SWP_FRAMECHANGED);}}
 void requestReset(){if(edit.count!=sim->scene.capacity||edit.contactBudget!=sim->config.contactBudget||edit.iterations!=sim->config.iterations){reconfigure=true;return;}AcquireSRWLockExclusive(&sim->requestLock);sim->requested=edit;ReleaseSRWLockExclusive(&sim->requestLock);sim->reset=true;}
 void controls(){
  ImGui_ImplDX12_NewFrame();ImGui_ImplWin32_NewFrame();ImGui::NewFrame();auto &io=ImGui::GetIO();
  if(!io.WantCaptureKeyboard){if(ImGui::IsKeyPressed(ImGuiKey_Space))sim->paused=!sim->paused;if(ImGui::IsKeyPressed(ImGuiKey_R))requestReset();if(ImGui::IsKeyPressed(ImGuiKey_F11))toggleFullscreen();if(ImGui::IsKeyPressed(ImGuiKey_H))hud=!hud;if(ImGui::IsKeyPressed(ImGuiKey_Home))camera.reset(displayExtent,displayScene);}
  if(!io.WantCaptureMouse){if(ImGui::IsMouseDragging(0)){camera.yaw-=io.MouseDelta.x*.006f;camera.pitch=std::clamp(camera.pitch+io.MouseDelta.y*.006f,-1.45f,1.45f);}if(ImGui::IsMouseDragging(1)||ImGui::IsMouseDragging(2)){float f=camera.distance*.0015f;camera.target[0]-=cosf(camera.yaw)*io.MouseDelta.x*f;camera.target[1]+=sinf(camera.yaw)*io.MouseDelta.x*f;camera.target[2]+=io.MouseDelta.y*f;}camera.distance=std::clamp(camera.distance*expf(-io.MouseWheel*.12f),2.f,300.f);}
  // Follow is a render-only centroid computed from the accepted GPU snapshot.
  if(hud){ImGui::SetNextWindowPos({24,24},ImGuiCond_Once);ImGui::SetNextWindowSize({420,720},ImGuiCond_Once);ImGui::Begin("Sunder / Physics3",nullptr,ImGuiWindowFlags_NoCollapse);ImGui::PushItemWidth(205);ImGui::Text("%s",displayScene==2?"Sphere rain / cutaway trough":(displayScene?"Colliding asteroid belts":"The living cube"));ImGui::TextDisabled("%u / %llu bodies admitted",displayActive,(unsigned long long)displayRequested);ImGui::ProgressBar(float(double(displayActive)/double(std::max<uint64_t>(1,displayRequested))),{0,3},"");
   if(ImGui::Button(sim->paused?"Play":"Pause"))sim->paused=!sim->paused;ImGui::SameLine();if(ImGui::Button("Step"))sim->single=true;ImGui::SameLine();if(ImGui::Button("Reset"))requestReset();
   if(ImGui::Combo("Scene",&edit.scene,"Living cube\0Asteroid belts\0Gravity trough (reference)\0")){uint64_t count=edit.count;int selected=edit.scene;edit=G7Config{};edit.count=count;edit.scene=selected;if(selected!=2){edit.radius=.4f;edit.batch=64;edit.spawnHz=8;edit.gravity=0;}requestReset();}
   for(int n:{100,500,1000}){char label[16];snprintf(label,16,n==1000?"1K":"%d",n);if(ImGui::Button(label)){edit.count=n;requestReset();}if(n!=1000)ImGui::SameLine();}
   ImGui::InputScalar("Bodies (exact)",ImGuiDataType_U64,&edit.count);ImGui::InputScalar("Spawn batch",ImGuiDataType_U32,&edit.batch);ImGui::InputFloat("Spawn / second",&edit.spawnHz,0,0,"%.4g");ImGui::TextDisabled("No preset cap; hardware, resources and GPU addressability still apply.");
   float speed=sim->speed;if(ImGui::InputFloat("Playback multiplier",&speed,0,0,"%.3g")&&std::isfinite(speed)&&speed>0)sim->speed=speed;ImGui::Text("Actual %.2fx / %.0f ticks per second",sim->paused?0:tps/128,sim->paused?0:tps);if(!sim->paused&&tps>0&&tps/128+.15<speed)ImGui::TextColored({1,.74f,.35f,1},"Physics throughput limits playback");
   if(ImGui::CollapsingHeader("Scene settings")){ImGui::InputInt("Seed",&edit.seed);ImGui::Combo("Density",&edit.density,"Open\0Compact\0");ImGui::InputFloat("Radius",&edit.radius);ImGui::InputFloat("Mass",&edit.mass);ImGui::InputFloat("Radius spread",&edit.radiusSpread);ImGui::InputFloat("Mass spread",&edit.massSpread);ImGui::InputFloat("Restitution (-1=preset)",&edit.restitution);ImGui::InputFloat("Friction (-1=preset)",&edit.friction);ImGui::InputFloat("Gravity X",&edit.gravityX);ImGui::InputFloat("Gravity Y",&edit.gravityY);ImGui::InputFloat("Gravity Z",&edit.gravity);ImGui::InputFloat("Initial rain speed Z",&edit.initialVz);
   ImGui::InputFloat("Cube speed",&edit.cubeSpeed);ImGui::InputFloat("Belt closing speed",&edit.beltClosingSpeed);
   ImGui::InputFloat("Belt spin",&edit.beltSpin);ImGui::InputFloat("Belt major radius (0=auto)",&edit.beltMajorRadius);
   ImGui::InputFloat("Belt minor radius (0=auto)",&edit.beltMinorRadius);
   ImGui::InputFloat("Emitter width X",&edit.emitterWidthX);ImGui::InputFloat("Emitter width Y",&edit.emitterWidthY);
   ImGui::InputFloat("Emitter height Z",&edit.emitterHeight);
   ImGui::InputFloat("Cell size (0=auto)",&edit.cell);ImGui::InputScalar("Contact budget (0=auto)",ImGuiDataType_U64,&edit.contactBudget);ImGui::InputScalar("Solver iterations",ImGuiDataType_U32,&edit.iterations);ImGui::InputScalar("Torus placement attempts",ImGuiDataType_U32,&edit.placementAttempts);ImGui::TextWrapped("Reset applies validated edits; native capacity changes rebuild the context.");}
   if(ImGui::Button("Camera reset"))camera.reset(displayExtent,displayScene);ImGui::SameLine();ImGui::BeginDisabled(displayScene==2);ImGui::Checkbox("Follow cloud",&follow);ImGui::EndDisabled();ImGui::Checkbox("Smooth motion",&smooth);ImGui::Checkbox("High quality",&quality);ImGui::SameLine();if(ImGui::Button("Fullscreen"))toggleFullscreen();if(ImGui::Button("Cinematic / H"))hud=false;
   if(!admissionError.empty())ImGui::TextWrapped("Capacity change rejected; existing simulation retained: %s",admissionError.c_str());if(!error.empty()){ImGui::TextColored({1,.44f,.25f,1},"Simulation stopped");ImGui::TextWrapped("%s",error.c_str());if(stats.error&1)ImGui::TextWrapped("1: contact capacity");if(stats.error&2)ImGui::TextWrapped("2: input / displacement");if(stats.error&4)ImGui::TextWrapped("4: contact residual / KKT");if(stats.error&8)ImGui::TextWrapped("8: state / orientation / penetration");if(stats.error&16)ImGui::TextWrapped("16: integrity / injected failure");ImGui::TextWrapped("Last accepted GPU state retained. Reset to recover.");}
   if(ImGui::CollapsingHeader("Native diagnostics")){ImGui::Text("Render %.1f FPS / GPU %.3f ms",fps,gpuUs/1000);ImGui::Text("Physics %.1f ticks/s",tps);ImGui::Text("GPU timeline %.3f ms / wall %.3f ms",stats.phases_us[7]/1000,hostUs/1000);ImGui::Text("Thread CPU %.3f ms (OS resolution)",cpuUs/1000);ImGui::Text("Accepted %u / rejected %u",accepted,rejected);ImGui::Text("Constraints %u / candidates %u",stats.contacts,stats.candidates);ImGui::Text("Maximum degree %u",stats.max_degree);ImGui::Text("Physics allocations %.2f MiB",stats.committed/1048576.);ImGui::Text("Render allocations %.2f MiB",renderCommitted/1048576.);ImGui::TextWrapped("Render images/buffers only; excludes ImGui and driver context.");ImGui::TextWrapped("%s",ph3_adapter(sim->p));ImGui::Text("Driver %s",driver[0]?driver:"unavailable");ImGui::Text("Seed %u / epoch %u",displaySeed,displayEpoch);ImGui::Text("Rejected admissions %u",rejectedBodies);ImGui::TextWrapped("Revision %s",G7_REVISION);ImGui::Text("Native slots %u / published %u",sim->scene.capacity,stats.published);ImGui::TextWrapped("Inactive slots are static parked bodies, excluded from admissions and drawing.");ImGui::TextWrapped(smooth?"Display: interpolation of accepted GPU states only.":"Display: latest copied accepted GPU state.");ImGui::TextWrapped("GPU timeline includes queue gaps during solver synchronization.");if(ImGui::Button("Sample contact topology"))sim->sample=true;if(sampleTick){ImGui::Text("Sample tick %u: geometric %u",sampleTick,geometric);ImGui::Text("Cross-belt %u / largest island %u",cross,island);}ImGui::TextWrapped("Sampling reads contact diagnostics and adds overhead. Trails and contact effects unavailable.");if(stats.error)ImGui::Text("Residual ratios N %.1f / T %.1f; penetration %.6f",validation.normal_ratio,validation.tangent_ratio,validation.max_penetration);}
   ImGui::Separator();ImGui::TextDisabled("Drag orbit / right-drag pan / wheel zoom");ImGui::TextDisabled("Space pause / R reset / F11 fullscreen");ImGui::PopItemWidth();ImGui::End();}
  ImGui::Render();
 }
 void frame(){
  double begin=now();wait();if(serial&&serial!=lastTimedSerial){lastTimedSerial=serial;UINT64 *v=nullptr;D3D12_RANGE range={0,16};check(timestampRead->Map(0,&range,(void**)&v));gpuUs=double(v[1]-v[0])*1e6/frequency;gpuSum+=gpuUs;gpuSampleCount++;D3D12_RANGE none={0,0};timestampRead->Unmap(0,&none);}
  RECT rect={};if(!GetClientRect(window,&rect)){quit=true;return;}UINT w=rect.right,h=rect.bottom;if(!w||!h){Sleep(10);return;}if(w!=width||h!=height)resize(w,h);
  check(allocator->Reset());check(list->Reset(allocator,nullptr));list->EndQuery(queries,D3D12_QUERY_TYPE_TIMESTAMP,0);Ph3Lease lease={};bool locked=TryAcquireSRWLockExclusive(&sim->lock)!=0,leased=false;
  if(locked){stats=sim->result;validation=sim->validation;accepted=sim->accepted;rejected=sim->rejected;cpuUs=sim->cpuUs;hostUs=sim->hostUs;tps=sim->tps;geometric=sim->geometric;cross=sim->cross;island=sim->island;sampleTick=sim->sampleTick;error=sim->error;
   if(ph3_acquire(sim->p,&lease)){
    if(snapshotRead&&displayEpoch==sim->epoch&&displayGeneration==lease.generation)ph3_release(sim->p,&lease);
    else{auto *resource=(ID3D12Resource*)ph3_native_resource(sim->p,&lease);if(!resource){ph3_release(sim->p,&lease);ReleaseSRWLockExclusive(&sim->lock);throw std::runtime_error("Invalid accepted-state lease");}
     bool history=snapshotRead&&displayEpoch==sim->epoch;
     barrier(previousSnapshot,snapshotRead?D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE:D3D12_RESOURCE_STATE_COMMON,D3D12_RESOURCE_STATE_COPY_DEST);
     if(history){barrier(snapshot,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_SOURCE);list->CopyBufferRegion(previousSnapshot,0,snapshot,0,192ull*sim->scene.capacity);barrier(snapshot,D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_COPY_DEST);}
     else{barrier(snapshot,snapshotRead?D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE:D3D12_RESOURCE_STATE_COMMON,D3D12_RESOURCE_STATE_COPY_DEST);list->CopyBufferRegion(previousSnapshot,0,resource,0,192ull*sim->scene.capacity);}
     list->CopyBufferRegion(snapshot,0,resource,0,192ull*sim->scene.capacity);barrier(snapshot,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);barrier(previousSnapshot,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
     previousPopulation=history?displayActive:0;double copied=now();copyInterval=history?std::clamp(copied-copyTime,.004,.2):1./60;copyTime=copied;snapshotRead=true;copiedFrames++;
     if(displayEpoch!=sim->epoch)camera.reset(sim->scene.extent,sim->config.scene);displayActive=sim->active;displayRequested=sim->config.count;displaySeed=sim->config.seed;rejectedBodies=sim->spawned-sim->active;displayScene=sim->config.scene;displayEpoch=sim->epoch;displayGeneration=lease.generation;displayExtent=sim->scene.extent;leased=true;
    }
   }
  }

  controls();UINT bi=swap->GetCurrentBackBufferIndex();barrier(backs[bi],D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_RENDER_TARGET);auto color=target(bi),z=dsv->GetCPUDescriptorHandleForHeapStart();float clear[4]={.025f,.037f,.052f,1};list->ClearRenderTargetView(color,clear,0,nullptr);list->ClearDepthStencilView(z,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);list->OMSetRenderTargets(1,&color,FALSE,&z);D3D12_VIEWPORT vp={0,0,float(width),float(height),0,1};D3D12_RECT sc={0,0,LONG(width),LONG(height)};list->RSSetViewports(1,&vp);list->RSSetScissorRects(1,&sc);
  if(snapshotRead&&(displayActive||displayScene==2)){Constants c={};float cy=cosf(camera.yaw),sy=sinf(camera.yaw),cp=cosf(camera.pitch),sp=sinf(camera.pitch);float f[3]={-cp*sy,-cp*cy,-sp},r[3]={cy,-sy,0},u[3]={-sy*sp,-cy*sp,cp};for(int i=0;i<3;i++){c.eye[i]=camera.target[i]-f[i]*camera.distance;c.forward[i]=f[i];c.right[i]=r[i];c.up[i]=u[i];}c.eye[3]=float(width);c.right[3]=float(height);c.lens[0]=1.8f*height/width;c.lens[1]=1.8f;c.lens[2]=.1f;c.lens[3]=1000.f/999.9f;c.population=displayActive;c.stride=sim->scene.capacity;c.scene=displayScene;c.quality=(quality?1u:0u)|(follow&&displayScene!=2?2u:0u)|(smooth?4u:0u);c.previousPopulation=previousPopulation;c.alpha=sim->paused?1.f:float(std::clamp((now()-copyTime)/copyInterval,0.,1.));list->SetGraphicsRootSignature(root);list->SetPipelineState(pipeline);list->SetGraphicsRootShaderResourceView(0,snapshot->GetGPUVirtualAddress());list->SetGraphicsRootShaderResourceView(2,previousSnapshot->GetGPUVirtualAddress());list->SetGraphicsRoot32BitConstants(1,sizeof(c)/4,&c,0);list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);if(displayScene==2){list->SetPipelineState(containerPipeline);list->DrawInstanced(6,4,0,0);list->SetPipelineState(pipeline);}list->DrawInstanced(6,displayActive,0,0);}
  list->SetDescriptorHeaps(1,&gui);ImGui_ImplDX12_RenderDrawData(ImGui::GetDrawData(),list);list->EndQuery(queries,D3D12_QUERY_TYPE_TIMESTAMP,1);list->ResolveQueryData(queries,D3D12_QUERY_TYPE_TIMESTAMP,0,2,timestampRead,0);barrier(backs[bi],D3D12_RESOURCE_STATE_RENDER_TARGET,D3D12_RESOURCE_STATE_PRESENT);check(list->Close());UINT64 next=serial+1;
  if(leased&&!ph3_track(sim->p,&lease,fence,next)){ph3_release(sim->p,&lease);ReleaseSRWLockExclusive(&sim->lock);throw std::runtime_error("Unable to track consumer fence");}
  ID3D12CommandList *lists[]={list};queue->ExecuteCommandLists(1,lists);HRESULT signal=queue->Signal(fence,next);if(leased)ph3_release(sim->p,&lease);if(locked)ReleaseSRWLockExclusive(&sim->lock);serial=next;unfenced=FAILED(signal);check(signal);check(swap->Present(1,0));double elapsed=now()-begin;minPopulation=std::min(minPopulation,snapshotRead?displayActive:0);maxPopulation=std::max(maxPopulation,snapshotRead?displayActive:0);renderedFrames++;fps=.94*fps+.06/std::max(.00001,elapsed);
 }
 void close(){if(unfenced&&SUCCEEDED(device->GetDeviceRemovedReason())){if(FAILED(queue->Signal(fence,serial))){fprintf(stderr,"Unfenced render work quarantined until process exit\n");return;}unfenced=false;}if(fence){try{wait();}catch(...){if(SUCCEEDED(device->GetDeviceRemovedReason())){fprintf(stderr,"Render work quarantined after wait failure\n");return;}}}ImGui_ImplDX12_Shutdown();ImGui_ImplWin32_Shutdown();ImGui::DestroyContext();for(auto &b:backs)drop(b);drop(depth);drop(snapshot);drop(previousSnapshot);drop(timestampRead);drop(queries);drop(containerPipeline);drop(pipeline);drop(root);drop(list);drop(allocator);drop(gui);drop(dsv);drop(rtv);drop(swap);drop(fence);drop(queue);drop(device);if(event)CloseHandle(event);}
};
static Renderer *renderer=nullptr;
static LRESULT CALLBACK wndproc(HWND w,UINT m,WPARAM a,LPARAM b){if(ImGui::GetCurrentContext()&&ImGui_ImplWin32_WndProcHandler(w,m,a,b))return 1;if(m==WM_CLOSE){DestroyWindow(w);return 0;}if(m==WM_DESTROY){PostQuitMessage(0);return 0;}return DefWindowProcW(w,m,a,b);}
int main(int argc,char **argv){
 Simulation sim;Renderer view;bool graphical=false;bool deviceLoss=argc>1&&strcmp(argv[1],"--device-loss-test")==0,removedForTest=false;int exitCode=0;
 try{
  projectDirectory();
  if(argc>1&&strcmp(argv[1],"--self-test")==0){
   sim.init();Ph3Lease lease={};if(!ph3_acquire(sim.p,&lease)||!ph3_native_resource(sim.p,&lease))throw std::runtime_error("Valid lease resource unavailable");
   if(ph3_close(sim.p))throw std::runtime_error("Closed context with outstanding lease");
   auto forged=lease;forged.generation++;if(ph3_native_resource(sim.p,&forged))throw std::runtime_error("Forged lease accepted");
   if(!ph3_release(sim.p,&lease)||ph3_native_resource(sim.p,&lease))throw std::runtime_error("Released lease remains usable");
   if(!ph3_reader_test(sim.p))throw std::runtime_error("Delayed tracked GPU reader failed");
   std::vector<float> before(size_t(48)*sim.scene.capacity),after(size_t(48)*sim.scene.capacity);if(!ph3_read(sim.p,before.data()))throw std::runtime_error("Pre-rejection read failed");float g[3]={};Ph3Result r={};
   if(!ph3_tick(sim.p,1.f/128,g,1,1,&r)||!r.error||r.published||!ph3_read(sim.p,after.data())||before!=after)throw std::runtime_error("Rejected tick altered accepted state");
   auto first=sim.scene.initial(2,true);if(!ph3_stage_append(sim.p,first.data(),0,2))throw std::runtime_error("Append birth stage failed");g[2]=-9.81f;if(!ph3_tick(sim.p,1.f/128,g,2,0,&r)||r.error||!ph3_read(sim.p,before.data()))throw std::runtime_error("Append initial tick failed");
   auto more=sim.scene.initial(3,true);if(!ph3_stage_append(sim.p,more.data(),2,3)||!ph3_tick(sim.p,1.f/128,g,2,1,&r)||!r.error||r.published||!ph3_read(sim.p,after.data())||before!=after||!ph3_drop_stage(sim.p))throw std::runtime_error("Append rejection changed accepted state");
   if(!ph3_stage_append(sim.p,more.data(),2,3)||!ph3_tick(sim.p,1.f/128,g,2,0,&r)||r.error||!ph3_read(sim.p,after.data()))throw std::runtime_error("Append commit failed");
   for(int axis=0;axis<3;axis++){double expected=before[axis*sim.scene.capacity]+(before[(axis+3)*sim.scene.capacity]+g[axis]/128.)/128.;if(fabs(after[axis*sim.scene.capacity]-expected)>2e-6)throw std::runtime_error("Birth rewound existing dynamic body");}
   printf("{\"rollback\":true,\"stale_lease_rejected\":true,\"delayed_reader\":true,\"append_preserves_dynamic\":true}\n");
  }else if(argc>1&&strcmp(argv[1],"--pacing-test")==0){
   sim.config.scene=0;sim.config.count=100;sim.config.batch=100;sim.config.gravity=0;sim.init();sim.tick();sim.tick();sim.thread=CreateThread(nullptr,0,Simulation::run,&sim,0,nullptr);if(!sim.thread)throw std::runtime_error("Pacing worker failed");double measured[4]={};float rates[4]={.25f,.5f,1,2};
   for(int i=0;i<4;i++){sim.speed=rates[i];Sleep(100);AcquireSRWLockExclusive(&sim.lock);unsigned begin=sim.accepted;ReleaseSRWLockExclusive(&sim.lock);double start=now();Sleep(1500);AcquireSRWLockExclusive(&sim.lock);measured[i]=(sim.accepted-begin)/(now()-start);ReleaseSRWLockExclusive(&sim.lock);}
   printf("{\"quarter_tps\":%.3f,\"half_tps\":%.3f,\"one_tps\":%.3f,\"two_tps\":%.3f}\n",measured[0],measured[1],measured[2],measured[3]);if(measured[2]<measured[0]*2.8||measured[3]<measured[1]*2.0)exitCode=2;
  }else if(argc>1&&strcmp(argv[1],"--verify")==0){sim.config.count=argc>2?atoi(argv[2]):512;sim.config.scene=argc>3?atoi(argv[3]):0;int ticks=argc>4?atoi(argv[4]):512;if(sim.config.scene!=2){sim.config.batch=256;sim.config.radius=.4f;sim.config.gravity=0;}sim.init();unsigned impacts=0,geometric=0,cross=0,maxContacts=0,sphereImpulses=0,planeImpulses=0,geometricSpheres=0,upwardReversals=0;std::vector<float> vz(sim.scene.capacity,0),acceptedState(size_t(48)*sim.scene.capacity);double gpu=0;std::vector<unsigned char> records(size_t(sim.config.contacts())*128);
   for(int i=0;i<ticks;i++){sim.tick();gpu+=sim.result.phases_us[7];maxContacts=std::max(maxContacts,sim.result.contacts);if(sim.result.error)break;if(sim.moving&&sim.result.contacts){if(!ph3_contacts(sim.p,records.data(),sim.result.contacts))throw std::runtime_error("Diagnostic readback failed");for(unsigned k=0;k<sim.result.contacts;k++){auto r=records.data()+k*128;unsigned a,b;double impulse,gap;memcpy(&a,r,4);memcpy(&b,r+4,4);memcpy(&impulse,r+16,8);memcpy(&gap,r+80,8);impacts+=impulse>0;geometric+=gap<=0;sphereImpulses+=impulse>0&&b<sim.scene.capacity;planeImpulses+=impulse>0&&b>=sim.scene.capacity;geometricSpheres+=gap<=0&&b<sim.scene.capacity;if(gap<=0&&a<unsigned(sim.config.count)&&b<unsigned(sim.config.count)&&sim.scene.authored[size_t(38)*sim.scene.capacity+a]!=sim.scene.authored[size_t(38)*sim.scene.capacity+b])cross++;}}if(!ph3_read(sim.p,acceptedState.data()))throw std::runtime_error("Accepted motion diagnostic failed");for(unsigned j=0;j<sim.active;j++){float current=acceptedState[5*sim.scene.capacity+j];if(vz[j]<-.5f&&current>.5f)upwardReversals++;vz[j]=current;}}
   printf("{\"adapter\":\"%s\",\"count\":%llu,\"scene\":%d,\"accepted\":%u,\"rejected\":%u,\"flags\":%u,\"max_constraints\":%u,\"positive_impulses\":%u,\"geometric_contacts\":%u,\"cross_belt_geometric\":%u,\"sphere_impulse_contacts\":%u,\"plane_impulse_contacts\":%u,\"geometric_sphere_contacts\":%u,\"upward_velocity_reversals\":%u,\"normal_ratio\":%.3f,\"tangent_ratio\":%.3f,\"mean_gpu_us\":%.3f,\"committed\":%llu}\n",ph3_adapter(sim.p),(unsigned long long)sim.config.count,sim.config.scene,sim.accepted,sim.rejected,sim.result.error,maxContacts,impacts,geometric,cross,sphereImpulses,planeImpulses,geometricSpheres,upwardReversals,sim.validation.normal_ratio,sim.validation.tangent_ratio,gpu/std::max(1u,sim.accepted+sim.rejected),(unsigned long long)sim.result.committed);if(sim.rejected&&sim.validation.normal){unsigned char raw[256];ph3_debug_control(sim.p,raw);unsigned a,b;double target,vn,tol,ln;memcpy(&a,raw+84,4);memcpy(&b,raw+88,4);memcpy(&target,raw+96,8);memcpy(&vn,raw+104,8);memcpy(&tol,raw+112,8);memcpy(&ln,raw+120,8);fprintf(stderr,"normal witness a=%u b=%u target=%.17g vn=%.17g tol=%.17g impulse=%.17g\n",a,b,target,vn,tol,ln);}exitCode=sim.rejected?2:0;
  }else if(argc>1&&strcmp(argv[1],"--fill-until-limit")==0){
   uint64_t current=512,chosenMax=G7_MAX_STATE_SLOTS,lastSuccess=0,firstFailure=0;
   uint32_t batch=32,trialTicks=8;double multiplier=2;unsigned attempts=0;
   for(int i=2;i<argc;i++){
    const std::string flag=argv[i];if(i+1>=argc)throw std::runtime_error("Missing fill benchmark argument value");
    const char *s=argv[++i];if(*s=='-')throw std::runtime_error("Negative fill benchmark argument");
    errno=0;char *end=nullptr;
    if(flag=="--multiplier"){
     multiplier=strtod(s,&end);
     if(errno==ERANGE||!end||*end||!std::isfinite(multiplier)||multiplier<=1)throw std::runtime_error("Fill multiplier must be a finite number >1");
     continue;
    }
    uint64_t n=strtoull(s,&end,10);
    if(errno==ERANGE||!end||*end)throw std::runtime_error("Invalid/overflowing fill benchmark integer");
    if(flag=="--start")current=n;
    else if(flag=="--max-count")chosenMax=n;
    else if(flag=="--batch"){if(!n||n>UINT32_MAX)throw std::runtime_error("Fill batch outside native uint32");batch=uint32_t(n);}
    else if(flag=="--ticks"){if(!n||n>UINT32_MAX)throw std::runtime_error("Fill ticks outside native uint32");trialTicks=uint32_t(n);}
    else throw std::runtime_error("Unknown fill benchmark option "+flag);
   }
   if(!current||!chosenMax||current>chosenMax)throw std::runtime_error("Invalid fill start/max");
   chosenMax=std::min(chosenMax,G7_MAX_STATE_SLOTS);
   std::string stopped="requested maximum tested";uint64_t attempted=0,lastAdmitted=0,lastCommitted=0;
   while(current<=chosenMax){
    attempted=current;attempts++;
    Simulation probe;
    try{
     probe.config.count=current;probe.config.batch=uint32_t(std::min<uint64_t>(batch,current));
     probe.init();
     while(probe.active<current&&!probe.fault)probe.tick();
     if(probe.fault||probe.active!=current)throw std::runtime_error(std::string("GPU rejected population fill: ")+probe.error);
     for(uint32_t t=0;t<trialTicks&&!probe.fault;t++)probe.tick();
     if(probe.fault)throw std::runtime_error(std::string("GPU rejected settled simulation: ")+probe.error);
     lastSuccess=current;lastAdmitted=probe.active;lastCommitted=probe.result.committed;
     probe.close();
    }catch(const std::exception&e){
     firstFailure=current;lastAdmitted=probe.active;lastCommitted=probe.result.committed;
     stopped=e.what();probe.close();break;
    }
    if(current==chosenMax)break;
    double candidate=std::ceil(double(current)*multiplier);
    if(candidate>double(chosenMax))current=chosenMax;
    else current=std::max<uint64_t>(current+1,uint64_t(candidate));
   }
   printf("{\"mode\":\"headless_native_capacity_ramp\",\"last_successful_population\":%llu,\"first_failed_population\":%llu,\"last_attempted_population\":%llu,\"last_admitted_population\":%llu,\"last_committed_bytes\":%llu,\"attempts\":%u,\"termination\":\"%s\",\"true_hardware_limit_proved\":false}\n",
    (unsigned long long)lastSuccess,(unsigned long long)firstFailure,(unsigned long long)attempted,
    (unsigned long long)lastAdmitted,(unsigned long long)lastCommitted,attempts,stopped.c_str());
   if(!lastSuccess)exitCode=2;
  }else{
   bool benchmark=argc>1&&strcmp(argv[1],"--render-bench")==0;
   if(benchmark){sim.config.count=1000;sim.config.batch=128;sim.config.spawnHz=4;}
   auto number=[](const char *s)->uint64_t{
    if(!s||!*s||*s=='-')throw std::runtime_error("Invalid unsigned numeric argument");
    errno=0;char *end=nullptr;unsigned long long v=strtoull(s,&end,10);
    if(errno==ERANGE||!end||*end)throw std::runtime_error(std::string("Invalid/overflowed integer: ")+s);
    return uint64_t(v);
   };
   auto positive32=[&](const char *s)->uint32_t{
    uint64_t v=number(s);if(!v||v>UINT32_MAX)throw std::runtime_error("Value outside native uint32 representation");return uint32_t(v);
   };
   auto decimal=[](const char *s)->float{
    errno=0;char *end=nullptr;float v=strtof(s,&end);
    if(errno==ERANGE||!end||*end||!std::isfinite(v))throw std::runtime_error(std::string("Invalid/overflowed float: ")+s);return v;
   };
   for(int i=2;i<argc;i++){
    auto option=std::string(argv[i]);if(option=="--frames"){i++;continue;}
    if(i+1>=argc)throw std::runtime_error("Missing value for "+option);
    const char *value=argv[++i];
    if(option=="--count")sim.config.count=number(value);
    else if(option=="--batch")sim.config.batch=positive32(value);
    else if(option=="--contacts")sim.config.contactBudget=number(value);
    else if(option=="--iterations")sim.config.iterations=positive32(value);
    else if(option=="--radius")sim.config.radius=decimal(value);
    else if(option=="--mass")sim.config.mass=decimal(value);
    else if(option=="--radius-spread")sim.config.radiusSpread=decimal(value);
    else if(option=="--mass-spread")sim.config.massSpread=decimal(value);
    else if(option=="--restitution")sim.config.restitution=decimal(value);
    else if(option=="--friction")sim.config.friction=decimal(value);
    else if(option=="--gravity-z")sim.config.gravity=decimal(value);
    else if(option=="--gravity-x")sim.config.gravityX=decimal(value);
    else if(option=="--gravity-y")sim.config.gravityY=decimal(value);
    else if(option=="--spawn-hz")sim.config.spawnHz=decimal(value);
    else if(option=="--cell")sim.config.cell=decimal(value);
    else if(option=="--initial-vz")sim.config.initialVz=decimal(value);
    else if(option=="--cube-speed")sim.config.cubeSpeed=decimal(value);
    else if(option=="--belt-closing-speed")sim.config.beltClosingSpeed=decimal(value);
    else if(option=="--belt-spin")sim.config.beltSpin=decimal(value);
    else if(option=="--belt-major-radius")sim.config.beltMajorRadius=decimal(value);
    else if(option=="--belt-minor-radius")sim.config.beltMinorRadius=decimal(value);
    else if(option=="--emitter-width-x")sim.config.emitterWidthX=decimal(value);
    else if(option=="--emitter-width-y")sim.config.emitterWidthY=decimal(value);
    else if(option=="--emitter-height")sim.config.emitterHeight=decimal(value);
    else if(option=="--seed")sim.config.seed=int(positive32(value));
    else if(option=="--scene")sim.config.scene=int(number(value));
    else if(option=="--placement-attempts")sim.config.placementAttempts=positive32(value);
    else throw std::runtime_error("Unknown option "+option);
   }
   sim.config.validate();sim.init();unsigned warmupAccepted=0;if(benchmark){while(sim.active<uint32_t(sim.config.count)){sim.tick();if(sim.fault)throw std::runtime_error("Native benchmark warmup rejected; inspect session evidence");}warmupAccepted=sim.accepted;}SetProcessDPIAware();WNDCLASSW wc={};wc.lpfnWndProc=wndproc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"SunderG7Native";wc.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));RegisterClassW(&wc);HWND w=CreateWindowExW(0,wc.lpszClassName,L"Sunder G7 - Native 3D",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,1600,900,nullptr,nullptr,wc.hInstance,nullptr);if(!w)throw std::runtime_error("Win32 window creation failed");view.init(w,sim);graphical=true;renderer=&view;if(benchmark){RECT client={0,0,1920,1080};AdjustWindowRect(&client,WS_OVERLAPPEDWINDOW,FALSE);SetWindowPos(w,nullptr,0,0,client.right-client.left,client.bottom-client.top,SWP_NOZORDER);}ShowWindow(w,SW_SHOW);if(benchmark){view.frame();view.wait();view.renderedFrames=0;view.copiedFrames=0;view.gpuSum=0;view.gpuSampleCount=0;view.lastTimedSerial=view.serial;view.minPopulation=UINT_MAX;view.maxPopulation=0;}sim.thread=CreateThread(nullptr,0,Simulation::run,&sim,0,nullptr);if(!sim.thread)throw std::runtime_error("Physics worker creation failed");MSG msg={};double started=now();int autoFrames=0;for(int i=1;i+1<argc;i++)if(strcmp(argv[i],"--frames")==0)autoFrames=atoi(argv[i+1]);unsigned frames=0;bool uiTest=argc>1&&strcmp(argv[1],"--ui-test")==0;
   while(!view.quit){while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){if(msg.message==WM_QUIT)view.quit=true;TranslateMessage(&msg);DispatchMessageW(&msg);}if(view.quit)break;size_t priorFrames=view.renderedFrames;view.frame();if(view.renderedFrames==priorFrames)continue;frames++;
    if(view.reconfigure){
     G7Config target=view.edit;G7Scene nextScene;Physics3 *fresh=nullptr;
     try{
      nextScene.generate(target);
      fresh=ph3_open(uint32_t(target.count),target.contacts(),target.iterations,0,"evidence/p10/build");
      if(!fresh)throw std::runtime_error("Native GPU admission failed; old accepted simulation is still running");
      auto initial=nextScene.initial(0,false);auto planes=nextScene.planes(target.scene);
      if(!ph3_seed(fresh,initial.data(),planes.data(),unsigned(planes.size()/4)))throw std::runtime_error("New native context refused the generated scene");
     }catch(const std::exception &e){
      if(fresh)ph3_close(fresh);
      view.admissionError=e.what();view.reconfigure=false;continue;
     }
     // The new context is fully admitted before retiring the old renderer/physics.
     sim.stop=true;if(sim.thread){WaitForSingleObject(sim.thread,INFINITE);CloseHandle(sim.thread);sim.thread=nullptr;}
     view.close();sim.close();
     sim.stop=false;sim.reset=false;sim.single=false;sim.paused=false;sim.sample=false;
     sim.p=fresh;sim.scene=std::move(nextScene);sim.config=target;sim.requested=target;
     sim.active=sim.spawned=sim.accepted=sim.rejected=0;sim.moving=target.scene==2;
     sim.fault=false;sim.nextSpawn=0;sim.result={};sim.validation={};sim.error[0]=0;sim.epoch++;
     view=Renderer{};view.init(w,sim);renderer=&view;
     sim.thread=CreateThread(nullptr,0,Simulation::run,&sim,0,nullptr);
     if(!sim.thread)throw std::runtime_error("Reconfigured physics worker creation failed");
     continue;
    }
    if(deviceLoss&&frames==90){sim.paused=true;AcquireSRWLockExclusive(&sim.lock);view.wait();Ph3Lease collect={};if(ph3_acquire(sim.p,&collect))ph3_release(sim.p,&collect);ID3D12Device5 *device5=nullptr;HRESULT hr=view.device->QueryInterface(IID_PPV_ARGS(&device5));if(FAILED(hr)){ReleaseSRWLockExclusive(&sim.lock);throw std::runtime_error("Controlled removal interface unavailable");}device5->RemoveDevice();drop(device5);removedForTest=true;ReleaseSRWLockExclusive(&sim.lock);}
    if(uiTest){
     if(frames==30)SetWindowPos(w,nullptr,0,0,1280,720,SWP_NOMOVE|SWP_NOZORDER);
     if(frames==60){view.edit.scene=1;view.requestReset();}
     if(frames==100){view.toggleFullscreen();view.camera.yaw+=.5f;view.camera.distance*=.8f;}
     if(frames==130)view.toggleFullscreen();
     if(frames==160){ShowWindow(w,SW_MINIMIZE);ShowWindow(w,SW_RESTORE);}
     if(frames==200){view.edit.scene=0;view.requestReset();}
     if(frames==250){sim.paused=true;sim.single=true;}
     if(frames==300)sim.paused=false;
    }
    if(autoFrames&&frames>=unsigned(autoFrames))view.quit=true;}
   AcquireSRWLockExclusive(&sim.lock);unsigned finalAccepted=sim.accepted,finalRejected=sim.rejected;ReleaseSRWLockExclusive(&sim.lock);if(finalRejected)exitCode=2;double meanGpu=view.gpuSum/std::max(uint64_t(1),view.gpuSampleCount);printf("{\"mean_gpu_render_us\":%.3f,\"gpu_snapshot_copies\":%u,\"render_frames\":%u,\"seconds\":%.3f,\"last_gpu_render_us\":%.3f,\"render_fps\":%.3f,\"width\":%u,\"height\":%u,\"scene_epochs\":%u,\"physics_accepted\":%u,\"physics_rejected\":%u,\"warmup_accepted\":%u,\"min_population\":%u,\"max_population\":%u}\n",meanGpu,view.copiedFrames,frames,now()-started,view.gpuUs,frames/std::max(.001,now()-started),view.width,view.height,view.displayEpoch,finalAccepted,finalRejected,warmupAccepted,view.minPopulation==UINT_MAX?0:view.minPopulation,view.maxPopulation);
  }
 }catch(const std::exception&e){fprintf(stderr,"G7 NO-GO: %s\n",e.what());if(deviceLoss&&removedForTest&&FAILED(view.device->GetDeviceRemovedReason())){printf("{\"controlled_device_loss_handled\":true,\"physical_removal\":\"NOT RUN\"}\n");exitCode=0;}else{if(graphical)MessageBoxA(nullptr,e.what(),"Sunder G7 - stopped",MB_ICONERROR);exitCode=1;}}
 sim.stop=true;if(sim.thread)WaitForSingleObject(sim.thread,INFINITE);if(graphical)view.close();sim.close();return exitCode;
}
