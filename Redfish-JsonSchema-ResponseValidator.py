#!/usr/bin/python
# Copyright Notice:
# Copyright 2017 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-JsonSchema-ResponseValidator/LICENSE.md

'''
python34 resourceValidate.py [args]
requirements:
Python 3
jsonschema -- pip(3) install jsonschema

The purpose of this program is to validate
redfish resources against DMTF json schemas.
There are three ways to run this:
1) against a directory of all 
     resources created by the mockup creator
2) selecting individual resources from
     that same directory 
     ( the -f option )
3) pulling a resource from an actual host 
     of a redfish service.
     ( -r and -i options )

resourceValidate.py -h
    to see options and defaults

NOTE:
If you are running from a OS in which the
   default Python is 2.x,
   the following script might help.

#!/usr/bin/env bash
cmd="/usr/bin/scl enable rh-python34"
args="$@"
$cmd "./resourceValidate.py $args " 

'''

import os,sys
import subprocess
import re
import json
import jsonschema
import getopt
import requests


def usage():
    print ('\nresourceValidate.py usage:')
    print ('  -h   display usage and exit')  
    print ('  -v   verbose')  
    print ('  -m   directory path to a mockup tree to validate against, default ./mockup-sim-pull')  
    print ('  -s   path to a local dir containing the json schema files to validate against, default ./DMTFSchemas')  
    print ('  -S   tell resourceValidate to get the schemaFiles from http://redfish.dmtf.org/schemas/v1/')
    print ('  -u   user name, default root')  
    print ('  -p   password, default calvin')  
    print ('  -e   error output file, default ./validate_errs')  
    print ('  -f   comma separated list of files to validate. if no -f, it validates entire mockup')  
    print ('  -r   hostname or IP address [:portno], default None')
    print ('  -i   url, --used with -r option to specify url for a live system. default /redfish/v1') 
    print ('  -x   comma separated list of patterns to exclude from errors') 
    print ('  -g   validate only resources which failed a previous run')
    print ('\n')
    print ('NOTE: if -r is specified, this will validate ')
    print ('         one resource (rest API) from a host')
    print ('NOTE: if -f is specified, this will validate individual')
    print ('         resources from the mockup directory')
    print ('NOTE: if -v is specified, resource JSON will be')
    print ('         printed to std out')
    print ('NOTE: if -g is specified, input files will be the files')
    print ('         found in a previous error file. If used with -v,')
    print ('         the output will include the resource JSON and the Schema')
    print ('\n')
    sys.exit()

def parseArgs(rv,argv):
    # parse args
    try:
        opts, args = getopt.gnu_getopt(argv[1:],"hvgSm:s:u:p:e:f:r:i:x:")
    except getopt.GetoptError:
        print("Error parsing options")
        usage()

    for opt,arg in opts:
        if opt in ('-h'): usage()
        elif opt in ('-v'): rv.verbose = True
        elif opt in ('-m'): rv.mockdir = arg
        elif opt in ('-s'): rv.schemadir = arg
        elif opt in ('-S'): rv.schemaorg = True
        elif opt in ('-u'): rv.user = arg
        elif opt in ('-p'): rv.password = arg
        elif opt in ('-e'): rv.errfile = arg
        elif opt in ('-f'): rv.files = arg
        elif opt in ('-r'): rv.ipaddr = arg
        elif opt in ('-i'): rv.url = arg
        elif opt in ('-x'): rv.excludes = arg
        elif opt in ('-g'): rv.doerrs = True


class ResourceValidate(object):
    def __init__(self, argv):
        self.verbose = False
        self.ipaddr = None
        self.url = '/redfish/v1'
        self.user = 'root'
        self.password = 'calvin'
        self.schemadir = './DMTFSchemas'
        self.schemaorg = False
        self.mockdir = './mockup-sim-pull'
        self.errfile = './validate_errs'
        self.files = None
        self.doerrs = False
        self.excludes = ''
        self.errcount = 0
        self.rescount = 0
        self.savedata = ''
        parseArgs(self,argv)

        self.orgurl = 'http://redfish.dmtf.org/schemas/v1/'

        if not self.doerrs:
            self.ef = open( self.errfile,'w')

        if self.excludes:
            self.excludes = self.excludes.split(',')

        if self.doerrs:
            self.doErrors()
        elif  self.ipaddr:
            self.valFromHost()
        elif self.files:
            self.traverseFiles()
        else:
            self.traverseDir()        

        print ('\n\n{} resources validated.'.format(self.rescount))
        if self.errcount:
            print ('\n{} errors. See {}'.format(self.errcount, self.errfile) )
        print ('\n\n')

    def doErrors(self):
        self.procerrs = []
        f = open(self.errfile,'r')
        lines  = f.readlines()
        f.close()
        self.files = ''
        for line in lines:
            line = line.strip()
            if self.mockdir in line:
                line = line.replace(self.mockdir,'')
                line = line.replace('/index.json','')
                self.files += line + ','
        self.traverseFiles()
        

    def valFromHost(self):
        ''' GET one resource from a host (rackmanager?)
            and validate against a DTMF schema.
        '''
        print( self.ipaddr + ':' + self.url )
        ret = self.get(self.ipaddr,self.url,self.user,self.password)
        if not ret:
            print('Invalid response from request')
            return

        if self.verbose: print(ret)
        try:
            data = json.loads(ret)
        except:
            print('bad json data')
            return
        if '@odata.type' not in data:
            msg = 'ERROR1: Missing @odata.type '
            self.errHandle(msg,self.url)
            return
        schname = self.parseOdataType(data)
        if schname[1]:
            schname = '.'.join(schname[:2])
        else:
            schname = schname[0] 
        schname += '.json'
        self.rescount += 1
        self.validate(data,schname,self.url)


    def traverseFiles(self):
        ''' read a list of resources specified
            with the -f option,
            and validate against a DTMF schema.
        '''
        files = self.files.split(',')
        files = list(set(files))
        for dirn in files:
            try:    
                fname = self.mockdir + '/' + dirn + '/' + 'index.json'
                print ('\n' + fname)
                f = open(fname,'r')
            except:
                print('index.json not found')
                continue
            try:
                data = f.read()
                if self.verbose: 
                    print(data)
                    print('\n')
                data = json.loads(data) 
            except:
                print('bad json data.')
                continue
            if '@odata.type' not in data:
                if 'redfish/index.json' not in fname:
                   if 'redfish/v1/odata/index.json' not in fname:
                       msg = 'ERROR1: Missing @odata.type '
                       self.errHandle(msg,fname)
                continue
            schname = self.parseOdataType(data)
            if schname[1]:
                schname = '.'.join(schname[:2])
            else:
                schname = schname[0] 
            schname += '.json'
            self.rescount += 1
            self.validate(data,schname,fname)

    def traverseDir(self):
        ''' walk a directory of resources 
            and validate against a DTMF schema.
        '''
        for dirn, subdir, filelist in  os.walk(self.mockdir):
          for fname in filelist:
            if fname == 'index.json':
              fname = dirn + '/' + fname
              print(fname)
              data = open(fname).read()
              if self.verbose: print(data)
              data = json.loads(data)
              if '@odata.type' not in data:
                if 'redfish/index.json' not in fname:
                   if 'redfish/v1/odata/index.json' not in fname:
                      msg = 'ERROR1: Missing @odata.type '
                      self.errHandle(msg,fname)
                continue
              schname = self.parseOdataType(data)
              if schname[1]:
                  schname = '.'.join(schname[:2])
              else:
                  schname = schname[0] 
              schname += '.json'
              self.rescount += 1
              self.validate(data,schname,fname)


    def validate(self,data,schname,fname):
        ''' this sample from the jsonschema website
        '''
        if self.schemaorg:  # get schema from DMT.org
            r = requests.get(self.orgurl + schname)
            if r.status_code != 200:
                print ('SCHEMA GET ERROR', r.status_code)
                return
            try:
                schema = json.loads(r.text)
            except:
                print('SCHEMA JSON invalid')
                return
        else:
            try:
                f = open(self.schemadir + '/' + schname,'r')
            except:
                self.errHandle('ERROR2: schema not found',fname,schname)
                return
            schema1 = f.read()
            schema = json.loads(schema1) 
            f.close() 
        try:
            v = jsonschema.Draft4Validator(schema)
            for error in sorted(v.iter_errors(data), key=str):
                x = False
                for item in self.excludes:
                    if item in error.message: x = True
                if not x:
                    self.errHandle(error.message,fname,schname)
        except jsonschema.ValidationError as e:
            print (e.message)
        if self.verbose: 
            print('\n',schema)
            print('\n')
 
    def errHandle(self,msg,fname,schname=''):
        print ('>>> ',msg)
        if not self.doerrs:
            outp = '\n\n' + fname + '\n  schema: ' + schname + '\n>>>' + msg
            self.ef.write(outp)
        self.errcount += 1

    def subp (self,cmd):
        p=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out, errors = p.communicate()
        ret = p.wait()
        if ret < 0:
            return ( errors )
        else:
            try:
                return (out.decode() )
            except:
                return out

    def get(self, host, url, user, password):
        ret = requests.get(host + url,auth=(user, password),verify=False)
        if ret.status_code == 200:
            return ret.text
        else: return None

    def parseOdataType(self,resource):
        ''' parse the @odata.type and return
            a usable tuple to construct 
            the schema file name.
        '''
        if not "@odata.type" in resource:
            print("Transport:parseOdataType: Error: No @odata.type in resource")
            return(None,None,None)

        resourceOdataType=resource["@odata.type"]
    
        #the odataType format is:  <namespace>.<version>.<type>   where version may have periods in it 
        odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9\._]*)\.([a-zA-Z0-9]*)$')  
        resourceMatch = re.match(odataTypeMatch, resourceOdataType)
        if(resourceMatch is None):
            # try with no version component
            odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9]*)$')
            resourceMatch = re.match(odataTypeMatch, resourceOdataType)
            if (resourceMatch is None):
                print("Transport:parseOdataType: Error parsing @odata.type")
                return(None,None,None)
            else:
                namespace = resourceMatch.group(1)
                version = None
                resourceType = resourceMatch.group(2)
        else:
            namespace=resourceMatch.group(1)
            version=resourceMatch.group(2)
            resourceType=resourceMatch.group(3)
    
        return(namespace, version, resourceType)

if __name__ == '__main__':
    rv = ResourceValidate(sys.argv)


