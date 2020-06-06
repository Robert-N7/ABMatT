#!/usr/bin/python
"""
ANoob's Brres Material Editor
For editing Mario Kart Wii files
"""
import getopt

from command import *

__version__ = "0.1.0"
USAGE = "{} -f <file> [-d <destination> -o -c <commandfile> -k <key> -v <value>\
 -n <name> -m <model> -i] "


def hlp():
    """ displays help message """
    helpstr = '''
====================================================================================
ANOOB'S BRRES MATERIAL TOOL
Version {}

      >>       >==>    >=>     >===>          >===>      >=>>=>    >=>   >=>>=>
     >>=>      >> >=>  >=>   >=>    >=>     >=>    >=>   >>   >=>   >> >=>    >=>
    >> >=>     >=> >=> >=> >=>        >=> >=>        >=> >>    >=>      >=>
   >=>  >=>    >=>  >=>>=> >=>        >=> >=>        >=> >==>>=>          >=>
  >=====>>=>   >=>   > >=> >=>        >=> >=>        >=> >>    >=>           >=>
 >=>      >=>  >=>    >>=>   >=>     >=>    >=>     >=>  >>     >>     >=>    >=>
>=>        >=> >=>     >=>     >===>          >===>      >===>>=>        >=>>=>

>=>>=>    >======>     >======>     >=======>   >=>>=>
>>   >=>  >=>    >=>   >=>    >=>   >=>       >=>    >=>
>>    >=> >=>    >=>   >=>    >=>   >=>        >=>
>==>>=>   >> >==>      >> >==>      >=====>      >=>
>>    >=> >=>  >=>     >=>  >=>     >=>             >=>
>>     >> >=>    >=>   >=>    >=>   >=>       >=>    >=>
>===>>=>  >=>      >=> >=>      >=> >=======>   >=>>=>

>=>       >=>       >>       >===>>=====> >=======> >======>     >=>       >>       >=>
>> >=>   >>=>      >>=>           >=>     >=>       >=>    >=>   >=>      >>=>      >=>
>=> >=> > >=>     >> >=>          >=>     >=>       >=>    >=>   >=>     >> >=>     >=>
>=>  >=>  >=>    >=>  >=>         >=>     >=====>   >> >==>      >=>    >=>  >=>    >=>
>=>   >>  >=>   >=====>>=>        >=>     >=>       >=>  >=>     >=>   >=====>>=>   >=>
>=>       >=>  >=>      >=>       >=>     >=>       >=>    >=>   >=>  >=>      >=>  >=>
>=>       >=> >=>        >=>      >=>     >=======> >=>      >=> >=> >=>        >=> >=======>

>===>>=====>     >===>          >===>      >=>
     >=>       >=>    >=>     >=>    >=>   >=>
     >=>     >=>        >=> >=>        >=> >=>
     >=>     >=>        >=> >=>        >=> >=>
     >=>     >=>        >=> >=>        >=> >=>
     >=>       >=>     >=>    >=>     >=>  >=>
     >=>         >===>          >===>      >=======>
====================================================================================

ABMatT is a tool for editing materials in Mario Kart Wii 'Brres' files. The tool can
do quick edits from the command line, or read in a command file for processing multiple
setting adjustments. This is particularly useful for editing a large
amount of materials or recreating a brres multiple times. Python regex matching is supported.
The tool is also smart about adjusting transparency. When setting to transparent it also
updates the comparison and reference settings, and the draw list to be xlu (fixing Harry Potter effect).

File command format in extended BNF:
    command = set | info;
    set   = 'set' space key ':' value [space 'for' space name] [space 'in' space container] EOL;
    info  = 'info' [space key] [space 'for' space name] [space 'in' space container] EOL;

Example file commands:
    set transparent:true for xlu.* in model course      # Sets all materials in course starting with xlu to transparent
    set shader:3 for ef_dushboard   # set any material in any model found matching 'ef_dushboard' to shader 3
    set scale:(1,1)                 # Sets the scale for all layers to 1,1
Example command line usage:
    ./AbMatT.py -f course_model.brres -o -k xlu -v disable -n opaque_material
This opens course_model.brres in overwrite mode and disables transparency for material 'opaque_material'.
For more Help or if you want to contribute visit https://github.com/Robert-N7/ABMatT
    '''
    print(helpstr.format(__version__))
    print("Usage: {}".format(USAGE))


def main(argv):
    ''' Main '''
    if not argv:
        hlp()
        sys.exit(0)
    try:
        opts, args = getopt.getopt(argv, "hf:d:ok:v:n:m:c:i",
                                   ["help", "file=", "destination=", "overwrite",
                                    "key=", "value=",
                                    "name=", "model=", "info", "commandfile="])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
    filename = ""
    destination = ""
    overwrite = False
    setting = ""
    value = ""
    name = ".*"
    model = ""
    commandfile = ""
    info = False
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            hlp()
            sys.exit()
        elif opt in ("-f", "--file"):
            filename = arg
        elif opt in ("-d", "--destination"):
            destination = arg
        elif opt in ("-o", "--overwrite"):
            overwrite = True
        elif opt in ("-k", "--key"):
            setting = arg
        elif opt in ("-v", "--value"):
            value = arg
        elif opt in ("-n", "--name"):
            name = arg
        elif opt in ("-m", "--model"):
            model = arg
        elif opt in ("-i", "--info"):
            info = True
        elif opt in ("-c", "--commandfile"):
            commandfile = arg
        else:
            print("Unknown option '{}'".format(opt))
            print(USAGE)
            sys.exit(2)
    if not filename:
        print("Filename is required")
        print(USAGE)
        sys.exit(2)

    cmds = []
    if destination:
        Command.DESTINATION = destination
        Brres.DESTINATION = destination
    if overwrite:
        Command.OVERWRITE = overwrite
        Brres.OVERWRITE = overwrite
    if setting:
        cmd = "set material " + setting + ":" + value + " for " + name + " in file " + filename
        if model:
            cmd += " model " + model
        cmds.append(Command(cmd))
        if info:
            cmds.append(Command("info"))
    if commandfile:
        # print("command file exists ")
        filecmds = load_commandfile(commandfile)
        # check for filename
        if not cmds and filecmds and filename:
            cmds = filecmds
            if not cmds[0].filename:
                cmds[0].filename = filename
        # print("File command length: {}".format(len(filecmds)))
        else:
            cmds = cmds + filecmds
    if info:
        cmd = "info material " + setting + " for " + name + " in file " + filename
        cmds.append(Command(cmd))
    if not cmds:
        print(USAGE)
    else:
        run_commands(cmds)
    # interactive mode maybe?


if __name__ == "__main__":
    USAGE = USAGE.format(sys.argv[0])
    main(sys.argv[1:])
