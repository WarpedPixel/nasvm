# nasvm
 Command line interface to manage VM's in FreeNAS/TrueNAS server.

 ## Installation

- make sure you have python 3.x installed
- install two libraries we depend on:

    `pip3 install websockets`

    `pip3 install keyring`

- copy nasvm.py to some place in your path
- optionally rename it to something better like nasvm, and make it executable with `chmod +x nasvm`
- you can set default NAS server for convenience with:
    `export NASVM_SERVER=MyFreeNAS` replacing MyFreeNAS by the hostname or IP of your server
- you can cache credentials if you simply use it once, the password you enter at the prompt will be cached in your OS credential storage.

## Examples

```
$ nasvm -s myfreenas -P list
root@myfreenas password:
  ID Name            PID Description
   1 Windows         1917
```
Now, the password is cached.

```
$ nasvm -s myfreenas list
  ID Name            PID Description
   1 Windows         1917
```
Or you can permanently set an environment variable so you never have to specify the server again (but you can override it with -s)

```
$ export NASVM_SERVER=myfreenas
$ nasvm list
  ID Name            PID Description
   1 Windows         1917
```

```
$ nasvm start 1         # (starts the VM listed above)
$ nasvm shutdown 1      # (attempts to shutdown the VM listed above, guest OS must respond)
$ nasvm halt 1          # (halts the VM listed above)
nasvm: operation on myfreenas ignored, use -f to force
$ nasvm --force halt 1  # (actually halts the VM listed above)
```


## Usage

```
$ nasvm --help
usage: nasvm [-h] [-u name] [-p pwd | -P] [-s addr] [-f] [-v]
             {list,ls,start,restart,halt,shutdown,shut,vnc} ...

Manage VM's in a FreeNAS/TrueNAS server

optional arguments:
  -h, --help            show this help message and exit
  -u name, --user name  user name for authentication (defaults to root)
  -p pwd, --password pwd
                        optional password for authentication (defaults to cached
                        password). Prompts if none available, successful password is
                        cached.
  -P, --prompt-password
                        force prompt for authentication password
  -s addr, --server addr
                        hostname or IP of NAS server (defaults to $NASVM_SERVER)
  -f, --force           force command to take destructive action
  -v, --verbosity       control verbosity, multiple increase verbosity up to 3

commands:
  valid commands (see more with nasvm command --help)

  {list,ls,start,restart,halt,shutdown,shut,vnc}
    list (ls)           list configured VMs
    start               start given VMs
    restart             halts given VMs immediately and restarts them
    halt                halts given VMs immediately
    shutdown (shut)     attempts to shutdown given VMs
    vnc                 list VNC attributes of given VMs

Passwords are cached in your local OS storage for passwords (e.g., keychain on
MacOS). You can manage that with the cross platform command 'keyring' using service
name 'NAS API'. Note that in FreeNAS up to 11.3-U4.1 only root can call the API.
```

## Implementation Notes

This is distributed as complete source you execute directly with your Python interpreter
in the future we might work on a proper packaging solution.

This uses the [websockets v2.0 API](https://www.truenas.com/docs/hub/additional-topics/api/ws_api/) from FreeNAS/TrueNAS.
