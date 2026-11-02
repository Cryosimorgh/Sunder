#pragma once
#include <cstdint>
#include <cstdio>
#include <limits>

// Text-backed UI fields: preserve incomplete edits until Apply. Never silently
// clamp typed values to an ImGui slider range or narrow a 64-bit population.
namespace g7ui {
inline bool parse_unsigned(const char *s, uint64_t &out) {
 if(!s || !*s)return false;
 uint64_t value=0;
 for(const unsigned char *p=(const unsigned char*)s;*p;p++){
  if(*p<'0'||*p>'9')return false;
  unsigned digit=*p-'0';
  if(value>(std::numeric_limits<uint64_t>::max()-digit)/10)return false;
  value=value*10+digit;
 }
 out=value;
 return true;
}
inline bool parse_positive_u32(const char *s,uint32_t &out){
 uint64_t value;
 if(!parse_unsigned(s,value)||!value||value>UINT32_MAX)return false;
 out=(uint32_t)value;
 return true;
}
template<size_t N>inline void write_unsigned(char (&target)[N],uint64_t value){
 std::snprintf(target,N,"%llu",(unsigned long long)value);
}
}
