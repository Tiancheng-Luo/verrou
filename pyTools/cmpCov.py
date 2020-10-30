#!/usr/bin/env python3
import re
import sys
from operator import itemgetter, attrgetter
import gzip
import os
import copy

import subprocess
import getopt
import functools


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



class openGz:
    """ Class to read/write  gzip file or ascii file """
    def __init__(self,name, mode="r", compress=None):
        self.name=name
        if os.path.exists(name+".gz") and compress==None:
            self.name=name+".gz"

        if (self.name[-3:]==".gz" and compress==None) or compress==True:
            self.compress=True
            self.handler=gzip.open(self.name, mode)
        else:
            self.compress=False
            self.handler=open(self.name, mode)

    def readline(self):
        if self.compress:
            return self.handler.readline().decode("ascii")
        else:
            return self.handler.readline()
    def readlines(self):
        if self.compress:
            return [line.decode("ascii") for line in self.handler.readlines()]
        else:
            return self.handler.readlines()


    def write(self, line):
        self.handler.write(line)


class bbInfoReader:
    """ Class to read trace_bb_info_log-PID(.gz) file and to provide a string describing
    a basic bloc defined by an index (called addr) from the MARK (debug symbol)

    After init the usual call are :
      .compressMarksWithoutSym(addr)
      .getStrToPrint(addr)

    """
    def __init__(self,fileName):
        self.read(fileName)

    def read(self,fileName):

        self.data={}
        self.dataMax={}
        self.dataCorrupted={}
        regularExp=re.compile("([0-9]+) : (.*) : (\S*) : ([0-9]+)")
        fileHandler=openGz(fileName)

        line=fileHandler.readline()
        counter=0
        while not line in [None, ''] :
            m=(regularExp.match(line.strip()))
            if m==None :
                print("error read fileName line:",[line])
                sys.exit()
            addr, sym, sourceFile, lineNum= m.groups()
            if addr in self.data:
                if not (sym,sourceFile,lineNum) in self.data[addr]:
                    self.data[addr]+=[(sym,sourceFile,lineNum)]
                if self.dataMax[addr]+1!= counter:
                    self.dataCorrupted[addr]=True
                self.dataMax[addr]=counter
            else:
                self.data[addr]=[(sym,sourceFile,lineNum)]
                self.dataMax[addr]=counter
                self.dataCorrupted[addr]=False
            counter+=1
            line=fileHandler.readline()


    def compressMarks(self, lineMarkInfoTab):
        lineToTreat=lineMarkInfoTab
        res=""
        while len(lineToTreat)!=0:
            symName=lineToTreat[0][0]
            select=[(x[1],x[2]) for x in lineToTreat if x[0]==symName ]
            lineToTreat=[x for x in lineToTreat if x[0]!=symName ]
            res+=" "+symName +"["+self.compressFileNames(select)+"] |"
        return res[0:-1]

    def compressMarksWithoutSym(self, addr):
        select=[(x[1],x[2]) for x in self.data[addr]  ]
        return self.compressFileNames(select)

    def compressFileNames(self, tabFile):
        tabToTreat=tabFile
        res=""
        while len(tabToTreat)!=0:
            fileName=tabToTreat[0][0]
            select=[(x[1]) for x in tabToTreat if x[0]==fileName ]
            tabToTreat=[x for x in tabToTreat if x[0]!=fileName ]
            res+=fileName +"("+self.compressLine(select)+")"
        return res

    def compressLine(self, lineTab):
        res=""
        intTab=[int(x) for x in lineTab]
        while len(intTab)!=0:
            begin=intTab[0]
            nbSuccessor=0
            for i in range(len(intTab))[1:]:
                if intTab[i]==begin+i:
                    nbSuccessor+=1
                else:
                    break
            if nbSuccessor==0:
                res+=str(begin)+","
            else:
                res+=str(begin)+"-"+str(begin+nbSuccessor)+","
            intTab=intTab[nbSuccessor+1:]
        return res[0:-1]

    def getStrToPrint(self, addr):
        return self.compressMarks(self.data[addr])

    def isCorrupted(self,addr):
        return self.dataCorrupted[addr]

    def print(self):
        for addr in self.data:
            print(self.compressMarks(self.data[addr]))

    def addrToIgnore(self, addr, ignoreList):
        listOfFile=[fileName for sym,fileName,num in self.data[addr]]
        for fileName in listOfFile:
            if fileName in ignoreList:
                return True
        return False

    def getListOfSym(self,addr):
        return list(set([sym for sym,fileName,num in self.data[addr]]))



class covReader:
    def __init__(self,pid, rep):
        self.pid=pid
        self.rep=rep
        self.bbInfo=bbInfoReader(self.rep+"/trace_bb_info.log-"+str(pid))
        covFile=openGz(self.rep+"/trace_bb_cov.log-"+str(pid))

        self.cov=self.readCov(covFile)

    def readCov(self, cov):
        res=[]
        currentNumber=-1
        dictRes={}
        while True:
            line=cov.readline()
            if line in [None,""]:
                if currentNumber!=-1:
                    res+=[dictRes]
                break
            if line=="cover-"+str(currentNumber+1)+"\n":
                if currentNumber!=-1:
                    res+=[dictRes]
                currentNumber+=1
                dictRes={}
                continue
            (index,sep, num)=(line).strip().partition(":")
            dictRes[index]=int(num)

        return res

    def writePartialCover(self,filenamePrefix=""):

        for num in range(len(self.cov)):
            resTab=[(index,num,self.bbInfo.getListOfSym(index),self.bbInfo.compressMarksWithoutSym(index)) for index,num in self.cov[num].items() ]
            resTab.sort( key= itemgetter(2,3,0)) # 2 sym  3 compress string 0 index

            handler=openGz(self.rep+"/"+filenamePrefix+"cover"+str(num)+"-"+str(self.pid),"w")
            for (index,count,sym, strBB) in resTab:
                handler.write("%d\t: %s\n"%(count,strBB))


class covMerge:
    """Class CovMerge allows to merge covers with counter of (success/failure) x (equal cover, diff cover).
    The method writePartialCover will compute from this counter a correlation coefficient for each covered bb"""

    def __init__(self, covRef):
        self.covRef=covRef
        print("covMerged with reference : %s"%(self.covRef.rep))
        self.init()

    def initCounterGlobal(self):
        self.success=0
        self.fail=0

    def incCounterGlobal(self,status):
        if status:
            self.success+=1
        else:
            self.fail+=1

    def initCounterLine(self):
        return (0,self.fail,0,self.success) #NbFailDiff, NbFailEqual, NbSuccessDiff, NbSuccessEqual
    def incCounterLine(self, counter, equalCounter, status):
        diff=0
        equal=0
        if equalCounter:
            equal=1
        else:
            diff=1

        if status:
            return (counter[0], counter[1] , counter[2]+diff, counter[3]+equal)
        else:
            return (counter[0]+diff, counter[1]+equal, counter[2], counter[3])

    def init(self):
        #init global counter
        self.initCounterGlobal()
        #load the first cover
        self.covMerged=[]
        for num in range(len(self.covRef.cov)): #loop over snapshots
            mergeDict={}
            for index,num in self.covRef.cov[num].items(): #loop over basic-bloc
                #get basic-bloc information
                sym=self.covRef.bbInfo.getListOfSym(index)[0]
                strLine=self.covRef.bbInfo.compressMarksWithoutSym(index)
                if not (sym,strLine) in mergeDict:
                    mergeDict[(sym,strLine)]=(num,self.initCounterLine())#bb not yet seen
                else:
                    mergeDict[(sym,strLine)]=(mergeDict[(sym,strLine)][0]+num,self.initCounterLine()) #bb already seen

            self.covMerged+=[mergeDict]


    def addMerge(self, cov, status):

        if len(cov.cov) != len(self.covRef.cov):
            print("addMerge : problem with the number of sync point")
            sys.exit()
        for num in range(len(cov.cov)): #loop over snapshots

            #use intermediate resDic to collapse bb with the same couple sym,strLine
            resDic={}
            for index,numLine in cov.cov[num].items():
                sym=cov.bbInfo.getListOfSym(index)[0]
                strLine=cov.bbInfo.compressMarksWithoutSym(index)
                if not (sym,strLine) in resDic:
                    resDic[(sym,strLine)]=numLine
                else:
                    resDic[(sym,strLine)]+=numLine
            #loop over collapse bb
            for ((sym, strLine), numLine) in resDic.items():
                if (sym,strLine)in self.covMerged[num]:
                    merged=self.covMerged[num][(sym,strLine)]
                    self.covMerged[num][(sym,strLine)]=(merged[0], self.incCounterLine(merged[1], merged[0]==numLine,status))
                else:
                    merged=(0, self.incCounterLine(self.initCounterLine(), False,status))
                    self.covMerged[num][(sym,strLine)]=merged
            #loop over bb not seen in this run
            for ((sym,strLine),merged) in self.covMerged[num].items():
                if not (sym,strLine)  in resDic:
                    self.covMerged[num][(sym,strLine)]=(merged[0], self.incCounterLine(merged[1], False,status))
        #update the global counter
        self.incCounterGlobal(status)


    def indicatorFromCounter(self, localCounter, name=""):
        nbFailDiff=   localCounter[0]
        nbFailEqual=  localCounter[1]
        nbSuccessDiff=localCounter[2]
        nbSuccessEqual=localCounter[3]

        nbSuccess=self.success
        nbFail=   self.fail

        if nbFailDiff +nbFailEqual !=nbFail:
            print("Assert Fail error")
            print("nbFail:",nbFail)
            print("nbFailDiff:",nbFailDiff)
            print("nbFailEqual:",nbFailEqual)
            return None


        if nbSuccessDiff +nbSuccessEqual !=nbSuccess:
            print("Assert Success error")
            print("nbSuccess:",nbSuccess)
            print("nbSuccessDiff:",nbSuccessDiff)
            print("nbSuccessEqual:",nbSuccessEqual)
            return None


        if name=="standard":
            return float(nbFailDiff + nbSuccessEqual)/ float(nbSuccess+nbFail)

        if name=="biased":
            return 0.5* (float(nbFailDiff)/ float(nbFail) + float(nbSuccessEqual)/float(nbSuccess))

        return None



    def writePartialCover(self,rep=".",filenamePrefix="", typeIndicator="standard"):

        for num in range(len(self.covMerged)): #loop over snapshots
            maxIndicator=0
            handler=openGz(rep+"/"+filenamePrefix+"coverMerged"+str(num),"w")
            partialCovMerged=self.covMerged[num]

            resTab=[(sym, strLine,
                     partialCovMerged[(sym,strLine)][0],
                     self.indicatorFromCounter(partialCovMerged[(sym,strLine)][1], typeIndicator ) ) for ((sym,strLine),counter) in partialCovMerged.items() ]

            resTab.sort( key= itemgetter(0,1)) # 2 sym  3 compress string 0 index
            for i in range(len(resTab)): #loop over sorted cover item
                sym,strLine,numLineRef,indicator=resTab[i]
                if indicator==None:
                    print("resTab[i]:",resTab[i])
                    print("partialCovMerged:",partialCovMerged[(sym,strLine)])
                    handler.write("none\t: %s\n"%(strLine))
                else:
                    maxIndicator=max(maxIndicator,indicator)
                    handler.write("%.2f\t: %s\n"%(indicator,strLine))

            print("Num: ", num , "\tMaxindicator: ", maxIndicator)

class statusReader:
    """Class to provide the status of a run"""
    # should maybe be a function instead of a class
    def __init__(self,pid, rep, runEval=None,runCmp=None, repRef=None):
        self.pid=pid
        self.rep=rep
        self.isSuccess=None
        if runCmp!=None:
            self.runCmpScript(runCmp, repRef)
            return
        if runEval!=None:
            self.runEvalScript(runEval)
            return
        self.read()

    def runCmpScript(self,runCmp,repref):
        subProcessRun=runCmdAsync([runCmp, repref,self.rep], os.path.join(self.rep, "cmpCmd%i"%(self.pid)))
        res=getResult(subProcessRun)
        if res==0:
            self.isSuccess=True
        else:
            self.isSuccess=False

    def runEvalScript(self,runEval):
        subProcessRun=runCmdAsync([runEval,self.rep], os.path.join(self.rep, "evalCmd%i"%(self.pid)))
        res=getResult(subProcessRun)
        if res==0:
            self.isSuccess=True
        else:
            self.isSuccess=False

    def read(self):
        pathName=os.path.join(self.rep, "dd.return.value")
        if os.path.exists(pathName):
            try:
                value=int(open(pathName).readline().strip())
                if value==0:
                    self.isSuccess=True
                else:
                    self.isSuccess=False
            except:
                print("Error while  reading "+pathName )
                self.isSuccess=None
        else:
            if self.rep.endswith("ref"):
                print("Consider ref as a success")
                self.isSuccess=True
            else:
                self.isSuccess=None

    def getStatus(self):
        return self.isSuccess


class cmpToolsCov:
    """Class to write partial cover of several executions :
    with writePartialCover the object write a partial cover for each execution
    with mergedCov the object write one merged partial cover with correlation information"""

    def __init__(self, tabPidRep, runCmp=None, runEval=None):
        self.tabPidRep=tabPidRep
        self.runCmp=runCmp
        self.runEval=runEval
        if runCmp!=None:
            self.refIndex=self.findRef(patternList=["ref","Ref","nearest","Nearest"])
            return
        if runEval!=None:
            self.refIndex=self.findRefDD(pattern="ref", optionalPattern="Nearest")
            return
        self.refIndex=self.findRefDD(pattern="ref", optionalPattern="dd.line/ref")


    def writePartialCover(self,filenamePrefix=""):
        """Write partial cover for each execution (defined by a tab of pid)"""
        for i in range(len(self.tabPidRep)):
            pid,rep=self.tabPidRep[i]
            cov=covReader(pid,rep)
            cov.writePartialCover(filenamePrefix)

    # def writeStatus(self):
    #     for i in range(len(self.tabPidRep)):
    #         pid,rep=self.tabPidRep[i]
    #         status=statusReader(pid,rep)
    #         success=status.getStatus()
    #         print( rep+":" + str(success))
    def getStatus(self,pid,rep):
        if self.runCmp!=None:
            status=statusReader(pid,rep, self.runCmp, self.tabPidRep[self.refIndex][1])
            return status.getStatus()
        if self.runEval!=None:
            status=statusReader(pid,rep, runEval=self.runEval)
            return status.getStatus()
        status=statusReader(pid,rep)
        return status.getStatus()

    def countStatus(self):
        """ Count the number of Success/Fail"""
        nbSuccess=0
        nbFail=0
        listPidRepoIgnore=[]
        for i in range(len(self.tabPidRep)):
            pid,rep=self.tabPidRep[i]
            success=self.getStatus(pid,rep)
            if success==None:
                listPidRepoIgnore+=[(pid,rep)]
            else:
                if success:
                    nbSuccess+=1
                else:
                    nbFail+=1
        for (pid,rep) in listPidRepoIgnore:
            print("directory ignored : "+rep)
            self.tabPidRep.remove((pid,rep))

        return (nbSuccess, nbFail)


    def findRefDD(self, pattern="ref", optionalPattern=None):
        "return the index of the reference (required for correlation)"
        if optionalPattern!=None:
            for index in range(len(self.tabPidRep)):
                (pid,rep)=self.tabPidRep[index]
                success=self.getStatus(pid,rep)
                if rep.endswith(pattern) and optionalPattern in rep and success:
                    return index
            print('Optional failed')
        for index in range(len(self.tabPidRep)):
            (pid,rep)=self.tabPidRep[index]
            success=self.getStatus(pid,rep)
            if rep.endswith(pattern) and success:
                return index
        print("Warning : pattern not found" )
        print("Switch to first Success reference selection")
        for index in range(len(self.tabPidRep)):
            pid,rep=self.tabPidRep[index]
            success=self.getStatus(pid,rep)
            if success:
                return index
        print("Error fail only : cmpToolsCov is ineffective" )
        sys.exit(42)

    def findRef(self, patternList):
        "return the index of the reference (required for correlation)"

        for index in range(len(self.tabPidRep)):
            rep=self.tabPidRep[index][1]
            for pattern in patternList:
                if pattern in rep:
                    return index
        return 0


    def writeMergedCov(self,estimator):
        """Write merged Cov with correlation indice  between coverage difference and sucess/failure status"""

        #check the presence of success and failure
        (nbSuccess, nbFail)=self.countStatus()
        print("NbSuccess: %d \t nbFail %d"%(nbSuccess,nbFail))
        if nbFail==0 or nbSuccess==0:
            print("mergeCov need Success/Fail partition")
            sys.exit()


        covMerged= covMerge(covReader(*self.tabPidRep[self.refIndex]))
        #Loop with addMerge to reduce memory peak

        printIndex=[int(float(p) * len(self.tabPidRep) /100.)  for p in (list(range(0,100,10))+[1,5])]
        printIndex +=[1,  len(self.tabPidRep)-1]

        for i in range(len(self.tabPidRep)):
            if i==self.refIndex:
                continue
            pid,rep=self.tabPidRep[i]
            covMerged.addMerge(covReader(pid,rep), self.getStatus(pid,rep))
            if i in printIndex:
                pourcent=float(i+1)/ float(len(self.tabPidRep)-1)
                if i >=self.refIndex:
                    pourcent=float(i)/ float(len(self.tabPidRep)-1)
                print( "%.1f"%(pourcent*100)    +"% of coverage data merged")
        #covMerged.writePartialCover(typeIndicator="standard")
        covMerged.writePartialCover(typeIndicator=estimator)



def extractPidRep(fileName):
    """extract the pid d'un fichier de la form trace_bb_cov.log-PID[.gz]"""
    rep=os.path.dirname(fileName)
    if rep=="":
        rep="."
    baseFile=os.path.basename(fileName)
    begin="trace_bb_cov.log-"
    if baseFile.startswith(begin):
        pid=int((baseFile.replace(begin,'')).replace(".gz",""))
        return (pid,rep)
    return None

def selectPidFromFile(fileNameTab):
    """Return a list of pid from a list of file by using extractPidRep"""
    return [extractPidRep(fileName)  for fileName in fileNameTab]





class config_option:
    def __init__(self,argv):
        #default Value
        self.genCov=False
        self.genCovCorrelation=False
        self.select_default=None
        self.run_cmp=None
        self.run_eval=None
        #parse Argv
        self.parseOpt(argv[1:])

    def usage(self):
        print ("Usage: genCov.py [--help] [--genCov] [--genCovCorrelation] [--select-default[=INT]] [--run-cmp=] file list of type trace_bb_cov.log* " )


    def parseOpt(self,argv):
        try:
            opts,args=getopt.getopt(argv, "h",["help","genCov","genCovCorrelation","select-default=", "run-cmp=", "run-eval="])
        except getopt.GetoptError:
            self.usage()
            sys.exit()

        for opt, arg in opts:
            if opt in ["-h", "--help"]:
                self.usage()
                sys.exit()
            if opt in ["--genCov"]:
                self.genCov=True
            if opt in ["--genCovCorrelation"]:
                self.genCovCorrelation=True
            if opt in ["--run-cmp"]:
                self.run_cmp=arg
            if opt in ["--run-eval"]:
                self.run_eval=arg
            if opt in ["--select-default"]:
                if arg=="0":
                    self.select_default=True
                else:
                    self.select_default=int(arg)

        #default configuartion : genCov
        if not (self.genCovCorrelation or self.genCov):
            self.genCov=True
        if self.run_eval!=None and self.run_cmp!=None:
            print("--run-cmp= and --run-eval= are incompatible option")
            sys.exit()

        self.listOfFiles=self.search_default_param()

        listArgToAdd=[]
        for arg in args:
            if arg not in self.listOfFiles:
                listArgToAdd+=[arg]
        self.listOfFiles=listArgToAdd +self.listOfFiles

        if len(self.listOfFiles)<1 and self.genCov:
            usage()
            print("--genCov required at least 1 argument")
            sys.exit()
        if len(self.listOfFiles)<2 and self.genCovCorrelation:
            usage()
            print("--genCovCorrelation required at least 2 arguments")
            sys.exit()

    def search_default_param(self):
        import pathlib
        addFile=[str(x) for x in pathlib.Path(".").rglob("trace_bb_cov.log*")]
        if self.select_default==True:
            return addFile
        if isinstance(self.select_default,int):
            return addFile[0:self.select_default]
        return []


if __name__=="__main__":
    options=config_option(sys.argv)

    cmp=cmpToolsCov(selectPidFromFile(options.listOfFiles), options.run_cmp, options.run_eval)
    if options.genCov:
        cmp.writePartialCover()
    if options.genCovCorrelation:
        cmp.writeMergedCov("biased")
#        cmp.writeMergedCov("standard")
