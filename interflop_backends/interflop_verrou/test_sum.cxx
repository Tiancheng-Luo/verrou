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


double computeSum(double init, double acc, int nb){
  double res=0;
  for(size_t i=0; i < nb ; i++){
    double add;
    interflop_verrou_add_double(res, acc,&add,context);
    res=add;
  }
  return res;
}



int main(int argc, char** argv){


  struct interflop_backend_interface_t ifverrou=interflop_verrou_init(&context);

  //  interflop_verrou_configure(VR_NEAREST, context);
  //  interflop_verrou_configure(VR_AVERAGE_DET, context);
  interflop_verrou_configure(VR_AVERAGE, context);
  //  interflop_verrou_configure(VR_RANDOM, context);
  struct timeval now;
  gettimeofday(&now, NULL);
  unsigned int pid = getpid();
  unsigned int seed = now.tv_usec + pid;


  verrou_set_seed (seed);

  verrou_set_debug_print_op(&print_debug);

  double res(computeSum(0, 0.1, 5000));
  double error=500-res;
  std::cout << std::setprecision(17);
  std::cout << "sum " << res<<" error " << error <<std::endl;


  interflop_verrou_finalyze(context);

  return 0;
}
