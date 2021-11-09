#!/usr/bin/env python3

# This file is part of Verrou, a FPU instrumentation tool.

# Copyright (C) 2014-2021 EDF
#   B. Lathuilière <bruno.lathuiliere@edf.fr>


# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307, USA.

# The GNU Lesser General Public License is contained in the file COPYING.

import numpy
import matplotlib.pyplot as plt
import sys
import os
import copy
import subprocess
import getopt
import functools
import glob

maxNbPROC=None

def failure():
    sys.exit(42)



def runCmdAsync(cmd, fname, envvars=None):
    """Run CMD, adding ENVVARS to the current environment, and redirecting standard
    and error outputs to FNAME.out and FNAME.err respectively.

    Returns CMD's exit code."""
    if envvars is None:
        envvars = {}

    with open("%s.out"%fname, "w") as fout:
        with open("%s.err"%fname, "w") as ferr:
            env = copy.deepcopy(os.environ)
            for var in envvars:
                env[var] = envvars[var]
            return subprocess.Popen(cmd, env=env, stdout=fout, stderr=ferr)

def getResult(subProcess):
    subProcess.wait()
    return subProcess.returncode



def verrou_run_stat(script_run, rep, listOfStat, maxNbPROC=None):
    if not os.path.exists(rep):
        os.mkdir(rep)
    listToRun=[]
    for roundingMode in ["nearest","upward","downward", "toward_zero","farthest","random","random_det","average", "average_det","float"]:
        for i in range(listOfStat[roundingMode]):
            name=("%s-%d")%(roundingMode,i)
            repName=os.path.join(rep,name)
            endFile=os.path.join(repName,"std")
            if not os.path.exists(endFile+".out"):
                os.mkdir(repName)
                #subProcessRun=runCmdAsync([script_run, repName],
                #                          endFile,
                #                          {"VERROU_ROUNDING_MODE":roundingMode })
                #getResult(subProcessRun)
                listToRun+=[{"script_run":script_run,
                             "repName": repName,
                             "output_prefix": endFile,
                             "env":{"VERROU_ROUNDING_MODE":roundingMode }}]


    listOfMcaKey=[ (x.split("-")[1:] +[listOfStat[x]])  for x in listOfStat.keys()  if x.startswith("mca")  ]
    for mcaConfig in listOfMcaKey:
        for i in range(mcaConfig[-1]):
            mode=mcaConfig[0]
            doublePrec=mcaConfig[1]
            floatPrec=mcaConfig[2]
            name=("mca%s_%s_%s-%d")%(mode,doublePrec, floatPrec,i)
            repName=os.path.join(rep,name)
            endFile=os.path.join(repName,"std")
            if not os.path.exists(endFile+".out"):
                print(repName)
                os.mkdir(repName)
                listToRun+=[{"script_run":script_run,
                             "repName": repName,
                             "output_prefix": endFile,
                             "env":{"VERROU_BACKEND":"mcaquad",
                                    "VERROU_MCA_MODE":mode,
                                    "VERROU_MCA_PRECISION_DOUBLE": doublePrec,
                                    "VERROU_MCA_PRECISION_FLOAT": floatPrec}}]
    if maxNbPROC==None:
        maxNbPROC=1
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=maxNbPROC) as executor:
        futures=[executor.submit(run, dicParam) for dicParam in listToRun]
        concurrent.futures.wait(futures)

def run(dicParam):
    print(dicParam["repName"], "begin")
    subProcessRun=runCmdAsync([dicParam["script_run"], dicParam["repName"]],
                              dicParam["output_prefix"],
                              dicParam["env"])
    getResult(subProcessRun)
    print(dicParam["repName"],"end")



def extractLoopOverComputation(rep, listOfStat, extractFunc):
    roundingModeList=["nearest","upward","downward", "toward_zero","farthest","random", "random_det","average","average_det","float"]
    resDict={}

    for roundingMode in roundingModeList :
        nbSample=listOfStat[roundingMode]
        resTab=[]
        if nbSample==0:
            resDict[roundingMode]=None
            continue
        for i in range(nbSample):
            name=("%s-%d")%(roundingMode,i)
            repName=os.path.join(rep,name)

            value=extractFunc(repName)
            resTab+=[value]
        resDict[roundingMode]=resTab


    listOfMcaKey=[ x  for x in listOfStat.keys()  if x.startswith("mca")  ]
    for mcaKey in listOfMcaKey:
        mcaConfig=(mcaKey.split("-")[1:] +[listOfStat[mcaKey]])
        nbSample=mcaConfig[-1]
        if nbSample==0:
            continue
        resTab=[]
        mode=mcaConfig[0]
        doublePrec=mcaConfig[1]
        floatPrec=mcaConfig[2]
        for i in range(nbSample):
            name=("mca%s_%s_%s-%d")%(mode,doublePrec, floatPrec,i)
            repName=os.path.join(rep,name)

            value=extractFunc(repName)
            resTab+=[value]

        resDict[mcaKey]=resTab

    return resDict


def verrou_extract_stat(extract_run, rep, listOfStat):
    def getValueData(repName):
        try:
            return float(subprocess.getoutput(extract_run +" "+ repName))
        except ValueError as err:
            print("Value Error while extracting value from :"+ extract_run +" "+ repName)
            sys.exit(42)


    return extractLoopOverComputation(rep,listOfStat, getValueData)

def verrou_extract_specific_pattern(extract_run, rep, listOfPattern, listOfName=None):
    def getValueData(repName):
        try:
            return float(subprocess.getoutput(extract_run +" "+ repName))
        except ValueError as err:
            print("Value Error while extracting value from :"+ extract_run +" "+ repName)
            sys.exit(42)

    if listOfName==None:
        listOfSplitName=[pattern.split("/") for pattern in listOfPattern ]
        #cleaning begin
        for i in range(len(listOfSplitName[0])):
            listOfName_i=[x[0] for x in listOfSplitName]
            if len(set(listOfName_i))==1:
                   listOfSplitName=[x[1:] for x in listOfSplitName]
            else:
                break
        #cleaning end
        for i in range(len(listOfSplitName[0])):
            listOfName_i=[x[-1] for x in listOfSplitName]
            if len(set(listOfName_i))==1:
                   listOfSplitName=[x[0:-1] for x in listOfSplitName]
            else:
                break
        #name generation
        listOfName=["/".join(x) for x in listOfSplitName]
        for i in range(len(listOfName)):
            if listOfName[i]=="":
                listOfName[i]="pattern"+str(i)
    res={}
    for i  in range(len(listOfPattern)):
        pattern=listOfPattern[i]
        listOfCatchPattern=[n for n in glob.glob(os.path.join(rep,pattern)) if os.path.isdir(n)]
        listOfValue=[getValueData(repName) for repName in listOfCatchPattern]

        res[listOfName[i]]=listOfValue
    return res


def verrou_extract_time(extract_time, rep, listOfStat):
    def getTimeData(repName):
        return [float(x) for x in (subprocess.getoutput(extract_time +" "+ repName)).split("\n")]
    return extractLoopOverComputation(rep,listOfStat, getTimeData)


def verrou_extract_var(extract_var, rep, listOfStat):
    def getVarData(repName):
        lines=(subprocess.getoutput(extract_var +" "+ repName)).split("\n")
        keys=lines[0].split()
        counter=0
        res={}
        for line in lines[1:]:
            values=[ float(x) for x in line.split()]
            if len(values)!=len(keys):
                print("invalid result : %(%s)"%(extract_var,repName))
                sys.exit()
            for i in range(len(keys)):
                res[(keys[i],counter)]= values[i]
            counter+=1

        return res
    return extractLoopOverComputation(rep,listOfStat, getVarData)




def prepareDataForParaview(dataTime,dataVar, rep):

    csvTime=open(os.path.join(rep, "paraviewTime.csv"),"w")
    first=True
    for rounding in dataTime:
        tabResult=dataTime[rounding]
        if tabResult!=None:
            for i in range(len(tabResult)):
                if first:
                    csvTime.write("index"+"\t" + "\t".join(["t"+str(t) for t in range(len(tabResult[i]))] ) +"\n")
                    first=False

                csvTime.write(rounding+"-"+str(i) +"\t"+ "\t".join([ str(x) for x in tabResult[i]])+"\n"  )
    csvTime.close()


    #select key
    first =True
    keys=None
    for rounding in dataVar:
        tabResult=dataVar[rounding]
        if tabResult!=None:
            for i in range(len(tabResult)):
                keysLocal=tabResult[i].keys()
                if first:
                    keys=list(keysLocal)
                    first=False
                else:
                    if keys!=list(keysLocal):
                        print("incoherent key")
                        sys.exit()
    keys.sort(key=lambda x:x[0])
    keys.sort(key=lambda x:x[1])

    csvParam=open(os.path.join(rep, "paraviewParam.csv"),"w")
    first=True
    for rounding in dataVar:
        tabResult=dataVar[rounding]
        if tabResult!=None:
            for i in range(len(tabResult)):
                if first:
                    csvParam.write("index"+"\t" + "\t".join([key+"-"+str(t) for (key,t) in keys ]) +"\n")
                    first=False
                csvParam.write(rounding+"-"+str(i) +"\t"+ "\t".join([ str(tabResult[i][x]) for x in keys])+"\n"  )
    csvParam.close()

def runParaview(rep):
    def getScriptPath():
        #the script is at the same place as this script
        return __file__.replace(os.path.basename(sys.argv[0]),"paraview_script.py")        

    cmd="paraview --script=%s"%(getScriptPath())
    print("paraview cmd: ", cmd)
    env = copy.deepcopy(os.environ)
    env["VERROU_PARAVIEW_DATA_PATH"]=rep
    process=subprocess.Popen(cmd, env=env, shell=True)

    def paraviewHelp():
        print(""" To enable link selection:
\t1) In Tools/ManageLink... click on Add
\t2) Select Selection Link (last item)
\t3) On left select Objects/TransposeTable1
\t4) On right select Objects/CSVReader2""")
    paraviewHelp()
    process.wait()


def listOfHistogram(listOfBrutData):
    maxValue=max([max([a for a in data if a!=float("inf")]) for data in listOfBrutData])
    minValue=min([min([a for a in data if a!=float("-inf")]) for data in listOfBrutData])

    numOfSpecialFloat=[ {"-inf":data.count(float("-inf")), "inf":data.count(float("inf")),"NaN":data.count(float("NaN")) } for data in listOfBrutData]
    listOfFilteredBrutData=[[x for x in data if x!=(float("inf")) and x!=(float("-inf")) and x!=float("NaN")] for data in listOfBrutData  ]

    bins=  (numpy.histogram(listOfBrutData[0], bins=40, range=[minValue, maxValue]))[1]
    return bins,listOfFilteredBrutData,numOfSpecialFloat

def plot_hist(data, png=False, relative=False):
    if relative!=False:
        plt.rcParams['text.usetex'] = True
    fig, ax = plt.subplots()

    plotWidth=1 #plot variable

    #selection of plot
    listOfScalar=[] # rounding mode plotted with vertical ligne
    listOfTab=[]    # rounding mode plotted with histogram

    #mcaMode=[ x  for x in data.keys()  if x.startswith("mca")  ]
    #verrouMode=["nearest","upward","downward", "toward_zero","farthest","random","average","float"]
#    for roundingMode in verrouMode+mcaMode:
    for roundingMode in sorted([x for x in data.keys()]):
        if data[roundingMode]==None:
            continue
        if len(data[roundingMode])==1:
            listOfScalar+=[roundingMode]
        if len(data[roundingMode])>1:
            listOfTab+=[roundingMode]

    convert= lambda x :x
    legend= "X"
    if relative!=False:

        if relative in ["nearest", "upward" ,"toward_zero", "farthest"]:
            valueRef=data[relative][0]
            latexName=relative.replace("_","\_")
            legend=r"$\frac{X-X_{%s}}{|X_{%s}|}$"%(latexName,latexName)
        else:
            valueRef=float(relative)
            legend=r"$\frac{X-%s}{|%s|}$"%(relative,relative)
        convert=lambda x:  (x-valueRef) /abs(valueRef)



    #extraction of same dataset size and histogram generation
    size=min([len(data[key]) for key in listOfTab  ])
#    hists=listOfHistogram([[convert(x) for x in data[key][0:size]] for key in listOfTab ])
    bins,datas, numOfSpecialFloat=listOfHistogram([[convert(x) for x in data[key][0:size] ] for key in listOfTab  ])

    lineColor=["orange","sienna","blue","red","green", "black", "purple","yellow"]
    lineColor+=["orange","blue","red","green", "black", "purple","yellow"]

    lineIndex=0

    #plot histogram
    maxHist=0
    name=[]
    name+=listOfTab
    plthandle=[]
    for i in range(len(name)):
        special=numOfSpecialFloat[i]["-inf"] + numOfSpecialFloat[i]["inf"]+numOfSpecialFloat[i]["NaN"]
        namei=name[i]
        if special!=0:
            namei+=":"
            for k in numOfSpecialFloat[i].keys():
                if numOfSpecialFloat[i][k]!=0:
                    namei+= k+"("+str(numOfSpecialFloat[i][k])+"):"
            namei=namei[0:-1]

        handle=plt.hist(datas[i],bins=bins, label=namei, linewidth=plotWidth,  alpha=0.6,color=lineColor[lineIndex])#, linestyle="-")
        lineIndex+=1
        plthandle+=[handle[0]]

    #plot vertical line
    nameDet=listOfScalar
    for mode in nameDet:
        value=convert(data[mode][0])
        #handle=plt.plot([value, value], [0, maxHist] , label=mode, linestyle='--', linewidth=plotWidth, color=lineColor[lineIndex])
        handle=plt.axvline(x=value,linestyle='--', linewidth=plotWidth, color=lineColor[lineIndex])

        modeStr=mode
        if plt.rcParams['text.usetex']:
            modeStr=mode.replace("_","\_")
        plt.text(value, 1., modeStr ,{'ha': 'left', 'va': 'bottom'},color=lineColor[lineIndex], transform=ax.get_xaxis_transform(),rotation=80)

        lineIndex+=1
        #plthandle+=[handle[0]]

#    plt.legend(plthandle, name+nameDet)

    plt.legend()
    plt.grid()
    plt.ylabel("#occurrence")
    if plt.rcParams['text.usetex']:
        plt.ylabel("$\#occurrence$")

    plt.xlabel(legend)

    if png!=False:
        plt.savefig(png,dpi=300,bbox_inches='tight')
    else:
        plt.show()




class config_stat:
    def __init__(self, argv):
        self.isMontcarlo=False
        self._nbSample=None
        self._rep="verrou.stat"
        self.listMCA=[]
        self.png=False
        self._hist=True
        self._time=False
        self.random=True
        self.average=True
        self.random_det=True
        self.average_det=True
        self._num_threads=None
        self._relative=False
        self._pattern=[]

        self.parseOpt(argv[1:])

        if len(self._pattern)!=0 and (self.isMontcarlo==True or self._nbSample!=None or self._time==True):
            print("--specific-pattern is incompatible with montecarlo, samples and time options")
            self.failure()

        if self._nbSample==None:
            self._nbSample=200

    def parseOpt(self,argv):
        try:
            opts,args=getopt.getopt(argv, "thms:r:p:",["time","help","montecarlo","no-random", "no-random_det","no-average", "no-average_det","samples=","rep=", "png=", "mca=", "num-threads=", "relative=", "specific-pattern="])
        except getopt.GetoptError:
            self.help()

        for opt, arg in opts:
            if opt in ("-h","--help"):
                self.help()
                sys.exit()
            if opt in ("-t","--time"):
                self._time=True
                self._hist=False
                continue
            if opt in ("-m","--montecarlo"):
                self.isMontcarlo=True
                continue
            if opt in ("-s","--samples"):
                self._nbSample=int(arg)
                continue
            if opt in ("--num-threads"):
                self._num_threads=int(arg)
                continue
            if opt in ("-r","--rep"):
                self._rep=arg
                continue
            if opt in ("--relative"):
                self._relative=arg
                continue
            if opt in ("-p","--png"):
                self.png=arg
                continue
            if opt in ("--no-random"):
                self.random=False
                continue
            if opt in ("--no-random_det"):
                self.random_det=False
                continue
            if opt in ("--no-average"):
                self.average=False
                continue
            if opt in ("--no-average_det"):
                self.average_det=False
                continue
            if opt in ["--specific-pattern"]:
                self._pattern+=[arg]
                continue
            if opt in ("--mca",):
                if arg=="":
                    self.listMCA+=["mca-rr-53-24"]
                else:
                    argSplit=arg.split("-")
                    if len(argSplit)!=4:
                        self.help()
                        self.failure()
                    else:
                        if not (argSplit[1] in ["rr","pb","mca"]):
                            self.help()
                            self.failure()
                        try:
                            a=int(argSplit[2])
                            b=int(argSplit[3])
                        except:
                            self.help()
                            self.failure()
                    self.listMCA+=["mca-"+arg]
                continue
            print("unknown option :", opt)

        if self._hist and len(self._pattern)==0:
            if len(args)>2:
                self.help()
                self.failure()
            self._runScript=self.checkScriptPath(args[0])
            self._extractScript=self.checkScriptPath(args[1])
        if len(self._pattern)!=0:
            if len(args)>1:
                self.help()
                self.failure()
            self._extractScript=self.checkScriptPath(args[0])
            self._runScript=None
        if self._time:
            if len(args)>3:
                self.help()
                self.failure()
            self._runScript=self.checkScriptPath(args[0])
            self._extractTimeScript=self.checkScriptPath(args[1])
            self._extractVarScript=self.checkScriptPath(args[2])

    def help(self):
        name=sys.argv[0]
        print( "%s [options] run.sh extract.sh or %s -t[or --time] [options] run.sh extractTime.sh extractVar.sh "%(name,name)  )
        print( "\t --no-random :  ignore random rounding mode")
        print( "\t --no-random_det :  ignore random_det rounding mode")
        print( "\t --no-average :  ignore average rounding mode")
        print( "\t --no-average_det :  ignore average_det rounding mode")
        print( "\t -r --rep=:  working directory [default verrou.stat]")
        print( "\t -s --samples= : number of samples")
        print( "\t --num-threads= : number of parallel run")
        print( "\t --relative= : float or value in [nearest,upward,downward,toward_zero,farthest]")
        print( "\t -p --png= : png file to export plot")
        print( "\t -m --montecarlo : stochastic analysis of deterministic rounding mode")
        print( "\t --mca=rr-53-24 : add mca ins the study")
        print( "\t --specific-pattern= : pattern of rep (useful to plot histogramm without run.sh)")

    def checkScriptPath(self,fpath):
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            return os.path.abspath(fpath)
        else:
            print("Invalid Cmd:"+str(sys.argv))
            print(fpath + " should be executable")
            self.help()
            self.failure()
    def failure(self):
        sys.exit(42)

    def runScript(self):
        return self._runScript

    def extractScript(self):
        return self._extractScript

    def extractTimeScript(self):
        return self._extractTimeScript

    def extractVarScript(self):
        return self._extractVarScript

    def isHist(self):
        return self._hist

    def isTime(self):
        return self._time

    def repName(self):
        return self._rep

    def getSampleConfig(self):
        nbDet=1
        if self.isMontcarlo:
            nbDet=self._nbSample
        nbSamples={"random":self._nbSample,
                   "random_det":self._nbSample,
                   "average":self._nbSample,
                   "average_det":self._nbSample,
                   "nearest":nbDet,
                   "upward":nbDet,
                   "downward":nbDet,
                   "toward_zero":nbDet,
                   "farthest":nbDet,
                   "float":0 }
        if not self.random_det:
            nbSamples["random_det"]=0
        if not self.random:
            nbSamples["random"]=0
        if not self.average:
            nbSamples["average"]=0
        if not self.average_det:
            nbSamples["average_det"]=0


        for mcaMode in self.listMCA:
               nbSamples[mcaMode]=self._nbSample
        return nbSamples

    def num_threads(self):
        return self._num_threads

    def relative(self):
        return self._relative

    def useSpecificPattern(self):
        return len(self._pattern)!=0

    def pattern(self):
        return self._pattern

if __name__=="__main__":
    conf=config_stat(sys.argv)
    nbSamples=conf.getSampleConfig()

    if conf.runScript()!=None:
        verrou_run_stat(conf.runScript(), conf.repName(), nbSamples, conf.num_threads())

    if conf.isHist():
        if not conf.useSpecificPattern():
            dataExtracted=verrou_extract_stat(conf.extractScript(), conf.repName(), nbSamples)
            plot_hist(dataExtracted, png=conf.png, relative=conf.relative())
        else:
            dataExtracted=verrou_extract_specific_pattern(conf.extractScript(), conf.repName(), conf.pattern())
            plot_hist(dataExtracted, png=conf.png, relative=conf.relative())

    if conf.isTime():
        dataTimeExtracted=verrou_extract_time(conf.extractTimeScript(), conf.repName(), nbSamples)
        dataVarExtracted=verrou_extract_var(conf.extractVarScript(), conf.repName(), nbSamples)

        prepareDataForParaview(dataTimeExtracted, dataVarExtracted,conf.repName())
        runParaview(conf.repName())
