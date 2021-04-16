#!/usr/bin/env python3

def sum(init, val, nb):
    res=init
    for i in range(nb):
        res+=val
    return res

if __name__=="__main__":
    nb=50000
    init=0
    res=sum(init,0.1,nb)
    error=res-(init+nb*0.1)

    print("sum %.17f error %.17f"%(res,error))
