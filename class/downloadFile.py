#coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2099 宝塔软件(http://bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Author: 黄文良 <2879625666@qq.com>
# +-------------------------------------------------------------------
import os,sys,public,json
class downloadFile:
    logPath = 'data/speed.json'
    timeoutCount = 0;
    oldTime = 0;
    #下载文件
    def DownloadFile(self,url,filename):
        try:
            path = os.path.dirname(filename)
            if not os.path.exists(path): os.makedirs(path)
            import urllib,socket,ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:pass
            socket.setdefaulttimeout(10)
            self.pre = 0;
            self.oldTime = time.time();
            if sys.version_info[0] == 2:
                urllib.urlretrieve(url,filename=filename,reporthook= self.DownloadHook)
            else:
                urllib.request.urlretrieve(url,filename=filename,reporthook= self.DownloadHook)
            self.WriteLogs(json.dumps({'name':'下载文件','total':0,'used':0,'pre':0,'speed':0}));
        except:
            if self.timeoutCount > 5: return;
            self.timeoutCount += 1
            time.sleep(5)
            self.DownloadFile(url,filename)
            
    #下载文件进度回调  
    def DownloadHook(self,count, blockSize, totalSize):
        used = count * blockSize
        pre1 = int((100.0 * used / totalSize))
        if self.pre != pre1:
            dspeed = used / (time.time() - self.oldTime);
            speed = {'name':'下载文件','total':totalSize,'used':used,'pre':self.pre,'speed':dspeed}
            self.WriteLogs(json.dumps(speed))
            self.pre = pre1

    #取下载进度
    def GetSpeed(self):
        speedLog = public.ReadFile(self.logPath)
        if not speedLog: return  {'name':'下载文件','total':0,'used':0,'pre':0,'speed':0}
        return json.loads(speedLog)
    
    #写输出日志
    def WriteLogs(self,logMsg):
        public.WriteFile(self.logPath,logMsg)