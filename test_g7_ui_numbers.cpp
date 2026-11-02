#include "g7_ui_numbers.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
int main(){
 uint64_t n=0;
 assert(g7ui::parse_unsigned("0",n)&&n==0);
 assert(g7ui::parse_unsigned("1000",n)&&n==1000);
 assert(g7ui::parse_unsigned("100001",n)&&n==100001);
 assert(g7ui::parse_unsigned("1000000",n)&&n==1000000);
 assert(g7ui::parse_unsigned("18446744073709551615",n)&&n==UINT64_MAX);
 for(const char *s:{"","-1","+1","1.5","1e6","12oops","18446744073709551616"," 123 ","999999999999999999999999999999999999999"})
  assert(!g7ui::parse_unsigned(s,n));
 uint32_t v=0;
 assert(g7ui::parse_positive_u32("1",v)&&v==1);
 assert(g7ui::parse_positive_u32("4294967295",v)&&v==UINT32_MAX);
 assert(!g7ui::parse_positive_u32("0",v));
 assert(!g7ui::parse_positive_u32("4294967296",v));
 char buf[64];
 g7ui::write_unsigned(buf,UINT64_MAX);
 assert(std::strcmp(buf,"18446744073709551615")==0);
 std::cout<<"PASS G7 native visual type-in precision/overflow contracts\n";
}
