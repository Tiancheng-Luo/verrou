#define DEBUG_PRINT_OP

#include "interflop_verrou.h"
#include <stdio.h>
#include <iostream>
#include <iomanip>
#include <vector>
#include <unistd.h>
#include <sys/time.h>

void print_debug(int nbArg, const char * op,const  double* a, const double* res){

  if(nbArg==1){
    std::cout << op << " : "<< a[0] << "->"<<&res << std::endl;
  }

  if(nbArg==2){
    std::cout << op << " : "<< a[0] << "," << a[1]<< "->"<<&res << std::endl;
  }

  if(nbArg==3){
    std::cout << op << " : "<< a[0] << "," << a[1]<< "," << a[2]<< "->"<<&res << std::endl;  
  }

} ;
void* context;


double computeDot(std::vector<double>& v1, std::vector<double>& v2, size_t blockSize){
  size_t totalSize=v1.size();
  if(totalSize!=v2.size()){
    std::cerr << "incoherent size"<< std::endl;
  }
  if(totalSize % blockSize !=0){
    std::cerr << "block size should divide total size" <<std::endl;
  }


  double res=0.;
  for(size_t iExtern=0; iExtern< size_t( totalSize / blockSize) ; iExtern++){
    double resLocal=0.;
    for(size_t iIntern=0; iIntern < blockSize; iIntern++){
      size_t i=iExtern *blockSize + iIntern;
      double mul;
      interflop_verrou_mul_double(v1[i],v2[i],&mul,context);
      double add;
      interflop_verrou_add_double(resLocal, mul,&add,context);
      resLocal=add;
    }
    double addGlob;
    interflop_verrou_add_double(resLocal, res ,&addGlob,context);
    res=addGlob;
  }
  return res;
}



int main(int argc, char** argv){


  struct interflop_backend_interface_t ifverrou=interflop_verrou_init(&context);

  //  interflop_verrou_configure(VR_NEAREST, context);
  interflop_verrou_configure(VR_AVERAGE_DET, context);
  interflop_verrou_configure(VR_RANDOM_DET, context);
  struct timeval now;
  gettimeofday(&now, NULL);
  unsigned int pid = getpid();
  unsigned int seed = now.tv_usec + pid;


  verrou_set_seed (seed);

  verrou_set_debug_print_op(&print_debug);


  std::vector<double> v1(128,0.1);
  std::vector<double> v2(128,0.1);
  std::vector<size_t> bTab({1,2,4,8,16,32});
  for(auto b: bTab){
    double dot1(computeDot(v1,v2,b));
    double dot2(computeDot(v1,v2,b));
    std::cout << std::setprecision(17);
    std::cout << "1-dot(" << b<<")" << dot1 << " "<< dot1 -1.28<<std::endl;
    std::cout << "2-dot(" << b<<")" << dot1 << " "<< dot1 -1.28<<std::endl;
  }


  interflop_verrou_finalyze(context);

  return 0;
}
