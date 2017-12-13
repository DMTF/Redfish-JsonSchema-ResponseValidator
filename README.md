# Redfish-JsonSchema-ResponseValidator 

Copyright 2017 Distributed Management Task Force, Inc. All rights reserved.

## About

***Redfish-JsonSchema-ResponseValidator.py*** is a Python3 utility used to validate any JSON resource against DMTF provided JSON schemas

### To run:

* Run from anywhere which has the proper Python3.4 or later environment,
* You can validate against local JsonSchema files in a local directory on the client, --OR-- you can tell the validator to use the JsonSchema files at the DMTF site.
  * if you use the option to access the DMTF hosted JsonSchema files, you must of course have internet access from the client to the DMTF site for http GETs.
* The typical use case is:
  * use Redfish-Mockup-Creator to pull a full mockup tree of all GET responses from a live system
  * then run resourceValidate pointing at the mockup tree to validate all of the responses in the mockup
* If you have one or two error cases, you can then re-run pointing at a specific file in the mockup tree,
  * Or you can point resourceValidate at a live system and validate a single URI response
* **See Examples below**

### [OPTIONS]:

```
Redfish-JsonSchema-ResponseValidator.py usage:
-h   display usage and exit
-v   verbose
-m   directory path to a mockup tree to validate against.   default: ./mockup-sim-pull
-s   path to a local directory containing the json schema files to validate against.  default ./DMTFSchemas
-S   Tells resourceValicate to get the schema from http://redfish.dmtf.org/schemas/v1/
-u   user name, default root
-p   password, default calvin
-e   error output path/filename, default ./validate_errs
-f   comma separated list of files to validate.  If -f is not specified, it will validate all index.json fils in the mockup
-r   hostname or IP address [:portno], default None
-i   url  --used with -r option to specify the url to test, default /redfish/v1
-x   comma separated list of patterns to exclude from errors
-g   validate only resources which failed a previous run
NOTE: if -r is specified, this will validate 
       one resource (rest API) from a host
NOTE: if -f is specified, this will validate individual
       resources from the mockup directory
NOTE: if -v is specified, resource JSON will be
       printed to std out
NOTE: if -g is specified, input files will be the files
       found in a previous error file. If used with -v,
       the output will include the resource JSON and the Schema

```

## Installation, Path, and Dependencies:

* clone repo with validateResource Redfish-JsonSchema-ResponseValidator directory
* If using the -m option, you must know the path to the mockup directory.
* Dependent modules:
  *  python3.4, 
  *  jsonschema, 
```
   NOTE: jsonschema should be installable by pip.
       # pip3 install jsonschema
       # This is the pypy implementation of the standard validator from json-schema.org  
```

  *  requests   `pip3 install requests`

## Examples:

```
Redfish-JsonSchema-ResponseValidator.py -m mockupdir
    -- walks the tree in mockupdir and validate every index.json file found

Redfish-JsonSchema-ResponseValidator.py -r 199.199.199.1[:port] or MyRedfishHost -i /redfish/vi/Systems
    -- validates one response from a live service

Redfish-JsonSchema-ResponseValidator.py -g -v [-e errorfile] > saveout
    -- validates the resources for a previous error file (-g)
       includes in the output the json resource and the json schema
       saves the standard out to be examined with an editor

NOTE: here is a shortcut bash script


```

## Known Issues

* filter tests to not try to validate /redfish   (the version response) since it does not contain an @odata.id prop
* filter tests to not try to validate /redfish/v1/odata/index.json  (the Odata Service Doc) since it does not have an @odata.id prop

## See Also:

* Redfish-Mockup-Creator
