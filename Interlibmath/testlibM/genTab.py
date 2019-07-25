#!/usr/bin/env python3
import sys
import math

def readFile(fileName):
    data=(open(fileName).readlines()) 
    keyData=data[0].split()
    brutData=[line.split() for line in data[1:]]

    res={}
    for index in range(len(keyData)):
        fileNameKey=fileName.replace("res","")
        dataIndex=[line[index] for line in brutData]
        res[keyData[index]]=(min(dataIndex),max(dataIndex))

    return res

def computeEvalError(dataNative, data):
    res={}
    for key in dataNative.keys():
        resIEEE=float(dataNative[key][0])        
        evalError=  - math.log2(max(abs(float(data[key][1]) - resIEEE),
                                    abs(float(data[key][0]) - resIEEE)) / resIEEE)
        res[key]=evalError
    return res

def loadRef(fileName, num=2):
    res={}
    for line in open(fileName):
        spline=line.split(":")
        typeRealtype=spline[0].split()[0]
        correction=spline[0].split()[1]
        [valueLow,valueUp]=spline[1].strip()[1:-1].split(",")
        if(float(valueUp)!=float(valueLow)):
            print("Please Increase the mpfi precision")
            sys.exit()
        value=float(valueUp)
        res[(typeRealtype, correction)]=value
    return res


def main(reference=None):
    

    output=open("tabAster.tex","w")
    outputReg=open("testReg","w")
    
    keys=["Native", "Randominterlibm", "Randomverrou", "Randomverrou+interlibm"]

    data={}
    strLatex=""
    for i in range(len(keys)):
        key=keys[i]
        data[key]=readFile("res"+key+".dat")

#        for key in sorted(keys[1:]):
    for i in range(1,len(keys)):
        key=keys[i]
        outputReg.write(key+"\n")
        evalError=computeEvalError(data["Native"], data[key])
        for keyCase in sorted(evalError.keys()):
            outputReg.write(keyCase +" "+str(evalError[keyCase])+"\n")
        
    output.write(r"\begin{table}" +" \n")
    output.write(r"\begin{tabular}{|c|cc|cc|}\hline" +" \n")
    output.write(r"precision  & \multicolumn{2}{c|}{Float }& \multicolumn{2}{c|}{Double }\\"+"\n"+
                 r"correction & Before& After & Before& After\\ \hline"+"\n")

    if reference!=None:
        output.write("IEEE Error & %.2f & %.2f & %.2f & %.2f"%(
                     reference[("Float","Before")],reference[("Float","After")],
                     reference[("Double","Before")], reference[("Double","After")])
                     + r"\\\hline"+"\n")
                
        
    
    for i in range(1,len(keys)):
        key=keys[i]            
        evalError=computeEvalError(data["Native"], data[key])
        lineStr=r"%s  "%(key.replace("Random",""))
        for typeFP in ["Float","Double"]:
            lineStr+=r"&%.2f &  %.2f  "%(evalError["BeforeCorrection_"+typeFP], evalError["AfterCorrection_"+typeFP]) 
        lineStr+=r"\\"+"\n"
        output.write(lineStr)
    output.write(r"\hline")
    output.write(r"\end{tabular}"+"\n")

    output.write(r"\caption{Number of significant bits for 4 implementations of function $f(a, a+3.ulp(a))$}"+"\n")

    output.write(r"\end{table}"+"\n")

    
    


if __name__=="__main__":
    reference=loadRef("reference.dat")
    if len(reference)!=4:
        reference=None
    main(reference)
