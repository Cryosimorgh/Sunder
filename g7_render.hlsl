ByteAddressBuffer state:register(t0);
ByteAddressBuffer previousState:register(t1);
cbuffer Camera:register(b0){float4 eye;float4 right;float4 up;float4 forward;float4 lens;uint population;uint stride;uint scene;uint quality;uint previousPopulation;float alpha;uint2 padding;};
float field(uint i,uint f){return asfloat(state.Load(4*(f*stride+i)));}
float3 displayPosition(uint i){
 float3 current=float3(field(i,0),field(i,1),field(i,2));
 if((quality&4)&&i<previousPopulation){float3 prior=float3(asfloat(previousState.Load(4*i)),asfloat(previousState.Load(4*(stride+i))),asfloat(previousState.Load(4*(2*stride+i))));return lerp(prior,current,alpha);}return current;
}
struct V{float4 position:SV_Position;float3 center:TEXCOORD0;float2 corner:TEXCOORD1;nointerpolation float radius:TEXCOORD2;nointerpolation float3 color:TEXCOORD3;};
V sphere_vs(uint vertex:SV_VertexID,uint i:SV_InstanceID){
 float2 corners[6]={float2(-1,-1),float2(-1,1),float2(1,1),float2(-1,-1),float2(1,1),float2(1,-1)};
 float3 cloudCenter=0;if(quality&2){for(uint j=0;j<population;j++)cloudCenter+=displayPosition(j);cloudCenter/=max(1u,population);}
 V o;float3 p=displayPosition(i)-eye.xyz-cloudCenter;float3 c=float3(dot(p,right.xyz),dot(p,up.xyz),dot(p,forward.xyz));
 o.radius=field(i,20);o.center=c;o.corner=corners[vertex];
 // Conservative perspective bounds; pixel shader ray-tests the true sphere.
 float z=max(lens.z,c.z-o.radius);float2 xy=c.xy+o.corner*o.radius*(1+abs(c.xy)/z);
 o.position=float4(xy.x*lens.x,xy.y*lens.y,c.z-lens.z,c.z);o.position.z=c.z*lens.w-lens.z*lens.w;
 float h=frac(sin(float(i)*12.9898)*43758.5453);
 o.color=scene==2?lerp(float3(.65,.76,.87),float3(.91,.90,.83),h):(scene?(field(i,38)>.5?float3(.83,.34,.13):float3(.15,.48,.80)):lerp(float3(.08,.40,.50),float3(.30,.72,.66),h));return o;
}
// The base mesh is scaled by two below: native slope .75, floor -8,
// end walls +/-16. The front end wall is a visual cutaway.
struct WallV {float4 position:SV_Position;float3 normal:TEXCOORD0;float3 world:TEXCOORD1;};
WallV container_vs(uint vertex:SV_VertexID,uint face:SV_InstanceID){
 uint indices[6]={0,1,2,0,2,3};uint corner=indices[vertex];float b=8.0/3.0;
 float3 corners[4];float3 normal;
 if(face==0){corners[0]=float3(-b,-8,-4);corners[1]=float3(b,-8,-4);corners[2]=float3(b,8,-4);corners[3]=float3(-b,8,-4);normal=float3(0,0,1);}
 else if(face==1){corners[0]=float3(-12,-8,3);corners[1]=float3(-b,-8,-4);corners[2]=float3(-b,8,-4);corners[3]=float3(-12,8,3);normal=float3(.6,0,.8);}
 else if(face==2){corners[0]=float3(b,-8,-4);corners[1]=float3(12,-8,3);corners[2]=float3(12,8,3);corners[3]=float3(b,8,-4);normal=float3(-.6,0,.8);}
 else{corners[0]=float3(-b,-8,-4);corners[1]=float3(b,-8,-4);corners[2]=float3(12,-8,3);corners[3]=float3(-12,-8,3);normal=float3(0,1,0);}
 WallV o;o.world=corners[corner]*2;o.normal=normal;float3 p=o.world-eye.xyz;
 float3 c=float3(dot(p,right.xyz),dot(p,up.xyz),dot(p,forward.xyz));
 o.position=float4(c.xy*float2(lens.x,lens.y),c.z*lens.w-lens.z*lens.w,c.z);return o;
}
float4 container_ps(WallV i):SV_Target{
 float diffuse=max(0,dot(i.normal,normalize(float3(-.4,-.5,1))));
 float3 color=float3(.54,.60,.68)*(.42+.58*diffuse);
 // A soft darkening at the trough foot makes the container shape readable.
 color*=.83+.17*saturate((i.world.z+8)/10);
 return float4(pow(color,1/2.2),1);
}
struct P{float4 color:SV_Target;float depth:SV_Depth;};
P sphere_ps(V i){
 float4 screen=i.position;
 float2 ndc=float2(screen.x/lens.x,screen.y/lens.y); // overwritten using viewport dimensions in eye.w/right.w
 float2 q=float2(2*screen.x/eye.w-1,1-2*screen.y/right.w);
 float3 ray=normalize(float3(q.x/lens.x,q.y/lens.y,1));
 float b=dot(ray,i.center),disc=b*b-dot(i.center,i.center)+i.radius*i.radius;if(disc<0)discard;
 float t=b-sqrt(disc);if(t<=lens.z)discard;float3 hit=ray*t,n=normalize(hit-i.center);
 float3 light=normalize(float3(-.6,.8,-.65)),view=-ray;float diffuse=max(0,dot(n,light));float spec=pow(max(0,dot(n,normalize(light+view))),(quality&1)?64:24);
 float rim=pow(1-max(0,dot(n,view)),3);float3 color=i.color*(.18+.82*diffuse)+spec*.7+rim*float3(.05,.13,.17);
 float fog=1-exp(-hit.z*.008);color=lerp(color,float3(.025,.037,.052),fog);
 P o;o.color=float4(pow(color,1/2.2),1);o.depth=lens.w-lens.z*lens.w/hit.z;return o;
}
