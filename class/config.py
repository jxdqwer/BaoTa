#coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板 x3
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2017 宝塔软件(http://bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Author: 黄文良 <287962566@qq.com>
# +-------------------------------------------------------------------

import public,re,sys,os
from BTPanel import session,admin_path_checks
from flask import request
class config:
    
    def getPanelState(self,get):
        return os.path.exists('/www/server/panel/data/close.pl');
    
    def setPassword(self,get):
        if get.password1 != get.password2: return public.returnMsg(False,'USER_PASSWORD_CHECK')
        if len(get.password1) < 5: return public.returnMsg(False,'USER_PASSWORD_LEN')
        public.M('users').where("username=?",(session['username'],)).setField('password',public.md5(get.password1.strip()))
        public.WriteLog('TYPE_PANEL','USER_PASSWORD_SUCCESS',(session['username'],))
        return public.returnMsg(True,'USER_PASSWORD_SUCCESS')
    
    def setUsername(self,get):
        if get.username1 != get.username2: return public.returnMsg(False,'USER_USERNAME_CHECK')
        if len(get.username1) < 3: return public.returnMsg(False,'USER_USERNAME_LEN')
        public.M('users').where("username=?",(session['username'],)).setField('username',get.username1.strip())
        public.WriteLog('TYPE_PANEL','USER_USERNAME_SUCCESS',(session['username'],get.username2))
        session['username'] = get.username1
        return public.returnMsg(True,'USER_USERNAME_SUCCESS')
    
    def setPanel(self,get):
        if not public.IsRestart(): return public.returnMsg(False,'EXEC_ERR_TASK');
        
        if get.domain:
            reg = "^([\w\-\*]{1,100}\.){1,4}(\w{1,10}|\w{1,10}\.\w{1,10})$";
            if not re.match(reg, get.domain): return public.returnMsg(False,'SITE_ADD_ERR_DOMAIN');
        isReWeb = False
        oldPort = public.GetHost(True);
        newPort = get.port;
        if oldPort != get.port:
            get.port = str(int(get.port))
            if self.IsOpen(get.port):
                return public.returnMsg(False,'PORT_CHECK_EXISTS',(get,port,))
            if int(get.port) >= 65535 or  int(get.port) < 100: return public.returnMsg(False,'PORT_CHECK_RANGE');
            public.writeFile('data/port.pl',get.port)
            import firewalls
            get.ps = public.getMsg('PORT_CHECK_PS');
            fw = firewalls.firewalls();
            fw.AddAcceptPort(get);
            get.port = oldPort;
            get.id = public.M('firewall').where("port=?",(oldPort,)).getField('id');
            fw.DelAcceptPort(get);
            isReWeb = True
        
        if get.webname != session['title']: 
            session['title'] = get.webname
            public.SetConfigValue('title',get.webname)

        limitip = public.readFile('data/limitip.conf');
        if get.limitip != limitip: public.writeFile('data/limitip.conf',get.limitip);
        
        public.writeFile('data/domain.conf',get.domain.strip())
        public.writeFile('data/iplist.txt',get.address)
        
        public.M('config').where("id=?",('1',)).save('backup_path,sites_path',(get.backup_path,get.sites_path))
        session['config']['backup_path'] = get.backup_path
        session['config']['sites_path'] = get.sites_path
        mhost = public.GetHost()
        if get.domain.strip(): mhost = get.domain
        data = {'uri':request.path,'host':mhost+':'+newPort,'status':True,'isReWeb':isReWeb,'msg':public.getMsg('PANEL_SAVE')}
        public.WriteLog('TYPE_PANEL','PANEL_SAVE',(newPort,get.domain,get.backup_path,get.sites_path,get.address,get.limitip))
        if isReWeb: public.restart_panel()
        return data


    def set_admin_path(self,get):
        get.admin_path = get.admin_path.strip()
        if get.admin_path == '': get.admin_path = '/'
        if get.admin_path != '/':
            if len(get.admin_path) < 6: return public.returnMsg(False,'安全入口地址长度不能小于6位!')
            if get.admin_path in admin_path_checks: return public.returnMsg(False,'该入口已被面板占用,请使用其它入口!')
            if not re.match("^/[\w\./-_]+$",get.admin_path):  return public.returnMsg(False,'入口地址格式不正确,示例: /my_panel')
        else:
            get.domain = public.readFile('data/domain.conf')
            if not get.domain: get.domain = '';
            get.limitip = public.readFile('data/limitip.conf')
            if not get.limitip: get.limitip = '';
            if not get.domain.strip() and not get.limitip.strip(): return public.returnMsg(False,'警告，关闭安全入口等于直接暴露你的后台地址在外网，十分危险，至少开启以下一种安全方式才能关闭：<a style="color:red;"><br>1、绑定访问域名<br>2、绑定授权IP</a>')

        admin_path_file = 'data/admin_path.pl'
        admin_path = '/'
        if os.path.exists(admin_path_file): admin_path = public.readFile(admin_path_file).strip()
        if get.admin_path != admin_path:
            public.writeFile(admin_path_file,get.admin_path)
            public.restart_panel()
        return public.returnMsg(True,'修改成功!');
               

    
    def setPathInfo(self,get):
        #设置PATH_INFO
        version = get.version
        type = get.type
        if public.get_webserver() == 'nginx':
            path = public.GetConfigValue('setup_path')+'/nginx/conf/enable-php-'+version+'.conf';
            conf = public.readFile(path);
            rep = "\s+#*include\s+pathinfo.conf;";
            if type == 'on':
                conf = re.sub(rep,'\n\t\t\tinclude pathinfo.conf;',conf)
            else:
                conf = re.sub(rep,'\n\t\t\t#include pathinfo.conf;',conf)
            public.writeFile(path,conf)
            public.serviceReload();
        
        path = public.GetConfigValue('setup_path')+'/php/'+version+'/etc/php.ini';
        conf = public.readFile(path);
        rep = "\n*\s*cgi\.fix_pathinfo\s*=\s*([0-9]+)\s*\n";
        status = '0'
        if type == 'on':status = '1'
        conf = re.sub(rep,"\ncgi.fix_pathinfo = "+status+"\n",conf)
        public.writeFile(path,conf)
        public.WriteLog("TYPE_PHP", "PHP_PATHINFO_SUCCESS",(version,type));
        public.phpReload(version);
        return public.returnMsg(True,'SET_SUCCESS');
    
    
    #设置文件上传大小限制
    def setPHPMaxSize(self,get):
        version = get.version
        max = get.max
        
        if int(max) < 2: return public.returnMsg(False,'PHP_UPLOAD_MAX_ERR')
        
        #设置PHP
        path = public.GetConfigValue('setup_path')+'/php/'+version+'/etc/php.ini'
        conf = public.readFile(path)
        rep = u"\nupload_max_filesize\s*=\s*[0-9]+M"
        conf = re.sub(rep,u'\nupload_max_filesize = '+max+'M',conf)
        rep = u"\npost_max_size\s*=\s*[0-9]+M"
        conf = re.sub(rep,u'\npost_max_size = '+max+'M',conf)
        public.writeFile(path,conf)
        
        if public.get_webserver() == 'nginx':
            #设置Nginx
            path = public.GetConfigValue('setup_path')+'/nginx/conf/nginx.conf'
            conf = public.readFile(path)
            rep = "client_max_body_size\s+([0-9]+)m"
            tmp = re.search(rep,conf).groups()
            if int(tmp[0]) < int(max):
                conf = re.sub(rep,'client_max_body_size '+max+'m',conf)
                public.writeFile(path,conf)
            
        public.serviceReload()
        public.phpReload(version);
        public.WriteLog("TYPE_PHP", "PHP_UPLOAD_MAX",(version,max))
        return public.returnMsg(True,'SET_SUCCESS')
    
    #设置禁用函数
    def setPHPDisable(self,get):
        filename = public.GetConfigValue('setup_path') + '/php/' + get.version + '/etc/php.ini'
        if not os.path.exists(filename): return public.returnMsg(False,'PHP_NOT_EXISTS');
        phpini = public.readFile(filename);
        rep = "disable_functions\s*=\s*.*\n"
        phpini = re.sub(rep, 'disable_functions = ' + get.disable_functions + "\n", phpini);
        public.WriteLog('TYPE_PHP','PHP_DISABLE_FUNCTION',(get.version,get.disable_functions))
        public.writeFile(filename,phpini);
        public.phpReload(get.version);
        return public.returnMsg(True,'SET_SUCCESS');
    
    #设置PHP超时时间
    def setPHPMaxTime(self,get):
        time = get.time
        version = get.version;
        if int(time) < 30 or int(time) > 86400: return public.returnMsg(False,'PHP_TIMEOUT_ERR');
        file = public.GetConfigValue('setup_path')+'/php/'+version+'/etc/php-fpm.conf';
        conf = public.readFile(file);
        rep = "request_terminate_timeout\s*=\s*([0-9]+)\n";
        conf = re.sub(rep,"request_terminate_timeout = "+time+"\n",conf);    
        public.writeFile(file,conf)
        
        file = '/www/server/php/'+version+'/etc/php.ini';
        phpini = public.readFile(file);
        rep = "max_execution_time\s*=\s*([0-9]+)\r?\n";
        phpini = re.sub(rep,"max_execution_time = "+time+"\n",phpini);
        rep = "max_input_time\s*=\s*([0-9]+)\r?\n";
        phpini = re.sub(rep,"max_input_time = "+time+"\n",phpini);
        public.writeFile(file,phpini)
        
        if public.get_webserver() == 'nginx':
            #设置Nginx
            path = public.GetConfigValue('setup_path')+'/nginx/conf/nginx.conf';
            conf = public.readFile(path);
            rep = "fastcgi_connect_timeout\s+([0-9]+);";
            tmp = re.search(rep, conf).groups();
            if int(tmp[0]) < int(time):
                conf = re.sub(rep,'fastcgi_connect_timeout '+time+';',conf);
                rep = "fastcgi_send_timeout\s+([0-9]+);";
                conf = re.sub(rep,'fastcgi_send_timeout '+time+';',conf);
                rep = "fastcgi_read_timeout\s+([0-9]+);";
                conf = re.sub(rep,'fastcgi_read_timeout '+time+';',conf);
                public.writeFile(path,conf);
                
        public.WriteLog("TYPE_PHP", "PHP_TIMEOUT",(version,time));
        public.serviceReload()
        public.phpReload(version);
        return public.returnMsg(True, 'SET_SUCCESS');
    
    
    #取FPM设置
    def getFpmConfig(self,get):
        version = get.version;
        file = public.GetConfigValue('setup_path')+"/php/"+version+"/etc/php-fpm.conf";
        conf = public.readFile(file);
        data = {}
        rep = "\s*pm.max_children\s*=\s*([0-9]+)\s*";
        tmp = re.search(rep, conf).groups();
        data['max_children'] = tmp[0];
        
        rep = "\s*pm.start_servers\s*=\s*([0-9]+)\s*";
        tmp = re.search(rep, conf).groups();
        data['start_servers'] = tmp[0];
        
        rep = "\s*pm.min_spare_servers\s*=\s*([0-9]+)\s*";
        tmp = re.search(rep, conf).groups();
        data['min_spare_servers'] = tmp[0];
        
        rep = "\s*pm.max_spare_servers \s*=\s*([0-9]+)\s*";
        tmp = re.search(rep, conf).groups();
        data['max_spare_servers'] = tmp[0];
        
        rep = "\s*pm\s*=\s*(\w+)\s*";
        tmp = re.search(rep, conf).groups();
        data['pm'] = tmp[0];
        
        return data


    #设置
    def setFpmConfig(self,get):
        version = get.version
        max_children = get.max_children
        start_servers = get.start_servers
        min_spare_servers = get.min_spare_servers
        max_spare_servers = get.max_spare_servers
        pm = get.pm
        
        file = public.GetConfigValue('setup_path')+"/php/"+version+"/etc/php-fpm.conf";
        conf = public.readFile(file);
        
        rep = "\s*pm.max_children\s*=\s*([0-9]+)\s*";
        conf = re.sub(rep, "\npm.max_children = "+max_children, conf);
        
        rep = "\s*pm.start_servers\s*=\s*([0-9]+)\s*";
        conf = re.sub(rep, "\npm.start_servers = "+start_servers, conf);
        
        rep = "\s*pm.min_spare_servers\s*=\s*([0-9]+)\s*";
        conf = re.sub(rep, "\npm.min_spare_servers = "+min_spare_servers, conf);
        
        rep = "\s*pm.max_spare_servers \s*=\s*([0-9]+)\s*";
        conf = re.sub(rep, "\npm.max_spare_servers = "+max_spare_servers+"\n", conf);
        
        rep = "\s*pm\s*=\s*(\w+)\s*";
        conf = re.sub(rep, "\npm = "+pm+"\n", conf);
        
        public.writeFile(file,conf)
        public.phpReload(version);
        public.WriteLog("TYPE_PHP",'PHP_CHILDREN', (version,max_children,start_servers,min_spare_servers,max_spare_servers));
        return public.returnMsg(True, 'SET_SUCCESS');
    
    #同步时间
    def syncDate(self,get):
        dateStr = public.HttpGet(public.GetConfigValue('home') + '/api/index/get_date')
        result = public.ExecShell('date -s "%s"' % dateStr);
        public.WriteLog("TYPE_PANEL", "DATE_SUCCESS");
        return public.returnMsg(True,"DATE_SUCCESS");
        
    def IsOpen(self,port):
        #检查端口是否占用
        import socket
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1',int(port)))
            s.shutdown(2)
            return True
        except:
            return False
    
    #设置是否开启监控
    def SetControl(self,get):
        try:
            if hasattr(get,'day'): 
                get.day = int(get.day);
                get.day = str(get.day);
                if(get.day < 1): return public.returnMsg(False,"CONTROL_ERR");
        except:
            pass
        
        filename = 'data/control.conf';
        if get.type == '1':
            public.writeFile(filename,get.day);
            public.WriteLog("TYPE_PANEL",'CONTROL_OPEN',(get.day,));
        elif get.type == '0':
            public.ExecShell("rm -f " + filename);
            public.WriteLog("TYPE_PANEL", "CONTROL_CLOSE");
        elif get.type == 'del':
            if not public.IsRestart(): return public.returnMsg(False,'EXEC_ERR_TASK');
            os.remove("data/system.db")
            import db;
            sql = db.Sql()
            result = sql.dbfile('system').create('system');
            public.WriteLog("TYPE_PANEL", "CONTROL_CLOSE");
            return public.returnMsg(True,"CONTROL_CLOSE");
            
        else:
            data = {}
            if os.path.exists(filename):
                try:
                    data['day'] = int(public.readFile(filename));
                except:
                    data['day'] = 30;
                data['status'] = True
            else:
                data['day'] = 30;
                data['status'] = False
            return data
        
        return public.returnMsg(True,"SET_SUCCESS");
    
    #关闭面板
    def ClosePanel(self,get):
        filename = 'data/close.pl'
        if os.path.exists(filename):
            os.remove(filename)
            return public.returnMsg(True,'开启成功')
        public.writeFile(filename,'True');
        public.ExecShell("chmod 600 " + filename);
        public.ExecShell("chown root.root " + filename);
        return public.returnMsg(True,'PANEL_CLOSE');
    
    
    #设置自动更新
    def AutoUpdatePanel(self,get):
        #return public.returnMsg(False,'体验服务器，禁止修改!')
        filename = 'data/autoUpdate.pl'
        if os.path.exists(filename):
            os.remove(filename);
        else:
            public.writeFile(filename,'True');
            public.ExecShell("chmod 600 " + filename);
            public.ExecShell("chown root.root " + filename);
        return public.returnMsg(True,'SET_SUCCESS');
    
    #设置二级密码
    def SetPanelLock(self,get):
        path = 'data/lock';
        if not os.path.exists(path):
            public.ExecShell('mkdir ' + path);
            public.ExecShell("chmod 600 " + path);
            public.ExecShell("chown root.root " + path);
        
        keys = ['files','tasks','config'];
        for name in keys:
            filename = path + '/' + name + '.pl';
            if hasattr(get,name):
                public.writeFile(filename,'True');
            else:
                if os.path.exists(filename): os.remove(filename);
                
    #设置PHP守护程序
    def Set502(self,get):
        filename = 'data/502Task.pl';
        if os.path.exists(filename):
            os.system('rm -f ' + filename)
        else:
            public.writeFile(filename,'True')
        
        return public.returnMsg(True,'SET_SUCCESS');
    
    #设置模板
    def SetTemplates(self,get):
        public.writeFile('data/templates.pl',get.templates);
        return public.returnMsg(True,'SET_SUCCESS');
    
    #设置面板SSL
    def SetPanelSSL(self,get):
        sslConf = '/www/server/panel/data/ssl.pl';
        if os.path.exists(sslConf):
            os.system('rm -f ' + sslConf);
            return public.returnMsg(True,'PANEL_SSL_CLOSE');
        else:
            os.system('pip insatll cffi==1.10');
            os.system('pip install cryptography==2.1');
            os.system('pip install pyOpenSSL==16.2');
            try:
                if not self.CreateSSL(): return public.returnMsg(False,'PANEL_SSL_ERR');
                public.writeFile(sslConf,'True')
            except Exception as ex:
                return public.returnMsg(False,'PANEL_SSL_ERR');
            return public.returnMsg(True,'PANEL_SSL_OPEN');
    #自签证书
    def CreateSSL(self):
        if os.path.exists('ssl/input.pl'): return True;
        import OpenSSL
        key = OpenSSL.crypto.PKey()
        key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
        cert = OpenSSL.crypto.X509()
        cert.set_serial_number(0)
        cert.get_subject().CN = '120.27.27.98';
        cert.set_issuer(cert.get_subject())
        cert.gmtime_adj_notBefore( 0 )
        cert.gmtime_adj_notAfter(86400 * 3650)
        cert.set_pubkey( key )
        cert.sign( key, 'md5' )
        cert_ca = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        private_key = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
        if len(cert_ca) > 100 and len(private_key) > 100:
            public.writeFile('ssl/certificate.pem',cert_ca)
            public.writeFile('ssl/privateKey.pem',private_key)
            return True
        return False
        
    #生成Token
    def SetToken(self,get):
        data = {}
        data[''] = public.GetRandomString(24);
    
    #取面板列表
    def GetPanelList(self,get):
        try:
            data = public.M('panel').field('id,title,url,username,password,click,addtime').order('click desc').select();
            if type(data) == str: data[111];
            return data;
        except:
            sql = '''CREATE TABLE IF NOT EXISTS `panel` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `title` TEXT,
  `url` TEXT,
  `username` TEXT,
  `password` TEXT,
  `click` INTEGER,
  `addtime` INTEGER
);'''
            public.M('sites').execute(sql,());
            return [];
    
    #添加面板资料
    def AddPanelInfo(self,get):
        
        #校验是还是重复
        isAdd = public.M('panel').where('title=? OR url=?',(get.title,get.url)).count();
        if isAdd: return public.returnMsg(False,'PANEL_SSL_ADD_EXISTS');
        import time,json;
        isRe = public.M('panel').add('title,url,username,password,click,addtime',(get.title,get.url,get.username,get.password,0,int(time.time())));
        if isRe: return public.returnMsg(True,'ADD_SUCCESS');
        return public.returnMsg(False,'ADD_ERROR');
    
    #修改面板资料
    def SetPanelInfo(self,get):
        #校验是还是重复
        isSave = public.M('panel').where('(title=? OR url=?) AND id!=?',(get.title,get.url,get.id)).count();
        if isSave: return public.returnMsg(False,'PANEL_SSL_ADD_EXISTS');
        import time,json;
        
        #更新到数据库
        isRe = public.M('panel').where('id=?',(get.id,)).save('title,url,username,password',(get.title,get.url,get.username,get.password));
        if isRe: return public.returnMsg(True,'EDIT_SUCCESS');
        return public.returnMsg(False,'EDIT_ERROR');
        pass
    
    #删除面板资料
    def DelPanelInfo(self,get):
        isExists = public.M('panel').where('id=?',(get.id,)).count();
        if not isExists: return public.returnMsg(False,'PANEL_SSL_ADD_NOT_EXISTS');
        public.M('panel').where('id=?',(get.id,)).delete();
        return public.returnMsg(True,'DEL_SUCCESS');
        pass 
    
    #点击计数
    def ClickPanelInfo(self,get):
        click = public.M('panel').where('id=?',(get.id,)).getField('click');
        public.M('panel').where('id=?',(get.id,)).setField('click',click+1);
        return True;
    
    #获取PHP配置参数
    def GetPHPConf(self,get):
        gets = [
                {'name':'short_open_tag','type':1,'ps':public.getMsg('PHP_CONF_1')},
                {'name':'asp_tags','type':1,'ps':public.getMsg('PHP_CONF_2')},
                {'name':'max_execution_time','type':2,'ps':public.getMsg('PHP_CONF_4')},
                {'name':'max_input_time','type':2,'ps':public.getMsg('PHP_CONF_5')},
                {'name':'memory_limit','type':2,'ps':public.getMsg('PHP_CONF_6')},
                {'name':'post_max_size','type':2,'ps':public.getMsg('PHP_CONF_7')},
                {'name':'file_uploads','type':1,'ps':public.getMsg('PHP_CONF_8')},
                {'name':'upload_max_filesize','type':2,'ps':public.getMsg('PHP_CONF_9')},
                {'name':'max_file_uploads','type':2,'ps':public.getMsg('PHP_CONF_10')},
                {'name':'default_socket_timeout','type':2,'ps':public.getMsg('PHP_CONF_11')},
                {'name':'error_reporting','type':3,'ps':public.getMsg('PHP_CONF_12')},
                {'name':'display_errors','type':1,'ps':public.getMsg('PHP_CONF_13')},
                {'name':'cgi.fix_pathinfo','type':0,'ps':public.getMsg('PHP_CONF_14')},
                {'name':'date.timezone','type':3,'ps':public.getMsg('PHP_CONF_15')}
                ]
        phpini = public.readFile('/www/server/php/' + get.version + '/etc/php.ini');
        
        result = []
        for g in gets:
            rep = g['name'] + '\s*=\s*([0-9A-Za-z_& ~]+)(\s*;?|\r?\n)';
            tmp = re.search(rep,phpini)
            if not tmp: continue;
            g['value'] = tmp.groups()[0];
            result.append(g);
        
        return result;


    def get_php_config(self,get):
        #取PHP配置
        get.version = get.version.replace('.','')
        file = session['setupPath'] + "/php/"+get.version+"/etc/php.ini"
        phpini = public.readFile(file)
        file = session['setupPath'] + "/php/"+get.version+"/etc/php-fpm.conf"
        phpfpm = public.readFile(file)
        data = {}
        try:
            rep = "upload_max_filesize\s*=\s*([0-9]+)M"
            tmp = re.search(rep,phpini).groups()
            data['max'] = tmp[0]
        except:
            data['max'] = '50'
        try:
            rep = "request_terminate_timeout\s*=\s*([0-9]+)\n"
            tmp = re.search(rep,phpfpm).groups()
            data['maxTime'] = tmp[0]
        except:
            data['maxTime'] = 0
        
        try:
            rep = r"\n;*\s*cgi\.fix_pathinfo\s*=\s*([0-9]+)\s*\n"
            tmp = re.search(rep,phpini).groups()
            
            if tmp[0] == '1':
                data['pathinfo'] = True
            else:
                data['pathinfo'] = False
        except:
            data['pathinfo'] = False
        
        return data
    
    #提交PHP配置参数
    def SetPHPConf(self,get):
        gets = ['display_errors','cgi.fix_pathinfo','date.timezone','short_open_tag','asp_tags','max_execution_time','max_input_time','memory_limit','post_max_size','file_uploads','upload_max_filesize','max_file_uploads','default_socket_timeout','error_reporting']
        filename = '/www/server/php/' + get.version + '/etc/php.ini';
        phpini = public.readFile(filename);
        for g in gets:
            rep = g + '\s*=\s*(.+)\r?\n';
            val = g+' = ' + get[g] + '\n';
            phpini = re.sub(rep,val,phpini);
        
        public.writeFile(filename,phpini);
        os.system('/etc/init.d/php-fpm-' + get.version + ' reload');
        return public.returnMsg(True,'SET_SUCCESS');
    
    #获取面板证书
    def GetPanelSSL(self,get):
        cert = {}
        cert['privateKey'] = public.readFile('ssl/privateKey.pem');
        cert['certPem'] = public.readFile('ssl/certificate.pem');
        cert['rep'] = os.path.exists('ssl/input.pl');
        return cert;
    
    #保存面板证书
    def SavePanelSSL(self,get):
        keyPath = 'ssl/privateKey.pem'
        certPath = 'ssl/certificate.pem'
        checkCert = '/tmp/cert.pl'
        public.writeFile(checkCert,get.certPem)
        if get.privateKey:
            public.writeFile(keyPath,get.privateKey);
        if get.certPem:
            public.writeFile(certPath,get.certPem);
        if not public.CheckCert(checkCert): return public.returnMsg(False,'证书错误,请检查!');
        public.writeFile('ssl/input.pl','True');
        return public.returnMsg(True,'证书已保存!');


    #获取配置
    def get_config(self,get):
        if 'config' in session: return session['config']
        data = public.M('config').where("id=?",('1',)).field('webserver,sites_path,backup_path,status,mysql_root').find();
        return data
    

    #取面板错误日志
    def get_error_logs(self,get):
        return public.GetNumLines('logs/error.log',2000)

    def is_pro(self,get):
        import panelAuth,json
        pdata = panelAuth.panelAuth().create_serverid(None)
        url = public.GetConfigValue('home') + '/api/panel/is_pro'
        pluginTmp = public.httpPost(url,pdata)
        pluginInfo = json.loads(pluginTmp)
        return pluginInfo
            
       
        