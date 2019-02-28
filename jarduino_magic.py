"""Implementation Jupyter IPython magic functions for
Arduino compile/execute load.
"""
# Copyright (c) Rene Juneau
# Distributed under the terms of the Modified BSD License.

# These imports required for the functions we run in our magic
import io
import os
import platform
import subprocess
import serial
import serial.tools.list_ports
import numpy
from pandas import *

# These imports required for the magic function decorators that process
# command line parameters for us
from IPython.core import magic_arguments
from IPython.core.magic import line_magic, cell_magic, line_cell_magic, Magics, magics_class


import matplotlib.pyplot as plt
import serial
import serial.tools.list_ports 

import argparse

def runexternal(command):
    p = subprocess.Popen(command)

    

def jardplotstatic(argv=None):
    ' Argument parser'
    ap = argparse.ArgumentParser(
                description = "Start plotter on serial output")
    ap.add_argument("-p", "--port", default = 'COM3', type = str,
                help = "serial port for arduino board")
    ap.add_argument("-g", "--graph", action = 'store_true', 
                help = "graph serial output")
    ap.add_argument("-s", "--speed", default = 9600, type = int,
                help = "Requires -g. Sets serial port speed. Default 9600")
    ap.add_argument("--points", default = 1000, type = int,
                help = "number of points to plot")
    ap.add_argument("--stack", action = 'store_true',
                help = "Stack instead of overlapping multiple plots")
    
    arg=ap.parse_args(argv)
    print('Plot options received:', argv)
    print('Points:', arg.points)
    print('Port:',arg.port)

    arduino_ports = [p.device for p in serial.tools.list_ports.comports()
                if 'Arduino' in p.description]

    if not arduino_ports:
        return("Arduino not found")
    elif len(arduino_ports) > 1:
        warning("Multiple Arduinos found - using the first")


    print("Connecting to port ", arduino_ports[0])
    port = serial.Serial(arduino_ports[0], arg.speed)   


    # Figure out how many entries per line
    # Read twice, just in case we start mid-line
    line=port.readline().decode('utf8')
    line=port.readline().decode('utf8')
    # get the number of values on the line
    vals = line.split()
    num_values = len(vals)
    # Initialise the array to the size
    x = []

    for dim in range(num_values):
        # Create an array for each dimension
        x.append([float(vals[dim])])

    lines = 0

    while  lines < arg.points:
        vals=port.readline().decode('utf8').split()
        floats = []
        # We need to ensure the values on the line are valid floats.
    # If not, just throw the line away
        try:
            for dim in range(num_values):
                floats.append(float(vals[dim]))
        except:
            break   #Throw it away
        else:
            lines +=1
            for dim in range(num_values):
                x[dim].append(floats[dim])
    

    x_axis = list(range(lines+1))
    for y_ax in x:
        #ts = Series(y_ax,index=x_axis)
        ts = Series(y_ax)
        #ts.plot(kind='bar', figsize=(15,5))
        ts.plot(figsize=(15,5))
        if arg.stack:
            plt.show()
    if not arg.stack:
        plt.show()
    port.close()
    












def redefinefile(filename, parms, cell):
    ''' Writes file from text cell and if parms specified,
        redefines the values in the sketch #define statements.
        Parms is a list in the form [['NAME1', 'VALUE1']...['NAMEn','VALUEn]]
    '''
    # if no #define parameters to changes, just dump it as is
    if not parms:
        with io.open(filename, 'w', encoding='utf-8') as f:
                f.write(cell)
    else:
        # Parameters gotta be parsed into list of values
        varlist = []
        for parm in parms:
            varlist.append(parm[0])
        # Open the file to write a line at a time
        f = open(filename,'w', encoding = 'utf-8')
        # Check every line for a #define with the values we're looking for
        for line in cell.splitlines():
            fields = line.split()
            if len(fields):  # If there's something on the line...
                if fields[0] =='#define':
                    if fields[1] in varlist:
                        index = varlist.index(fields[1])
                        # Python is clever enough to parse out the field as
                        # string or int. We force it to string to make the
                        # rest of the processing simpler
                        value = str(parms[index][1])
                        # If it's a string, add the quotes before we rewrite
                        if not value.isnumeric():
                            value = "'"+ value + "'"
                        line = '#define ' + fields[1] +' ' + value
            f.write(line+'\n')
        f.close()        
    



#######
# Utility functions

# Return list of Arduino ports
def get_arduino_ports():
    return([p.device for p in serial.tools.list_ports.comports()
                            if 'Arduino' in p.description])

# Create our overall class - JarduinoMagics
# The class could contain multiple magics.
# JarduinoMagics will be registered in the Jupyter Ipython kernel at the end
# of this file. That makes it available in the notebook
 
@magics_class
class JarduinoMagics(Magics):
    """Magics to save, compile and load Arduino code from a Python cell
    """
    ###############################
    # Magic: jarduino
    #
    # This magic saves, compiles and optionally loads the Arduino found in the cell after the
    # %%jarduino <filename>
    
    # It's a cell magic (@cell_magic) because it's going access the full
    # contents of the cell - the Arduino code we want to compile  and load
    # The @ things are function decorators to manage the command line parameters
    
    @cell_magic
    
    # This sets us up to use the built-in Jupyter magics arguments toolkit
    @magic_arguments.magic_arguments()
    # We have an @magics_argument.argument line for each parameter.
    # We can have as many as we want.
    # The first arguments are flags - enabled or not.
    # 

    @magic_arguments.argument('--check', '-c', action='store_true',
        help='Check/compile only. Do not load to Arduino board')
    @magic_arguments.argument('--verbose', '-v', action='store_true',
        help='Enable verbose mode during build/load')
    #The next ones provide a parameter value
    #   The directory name
    @magic_arguments.argument('--dir', '-d', 
        help='The directory within sketches to store the file')
    #   The port
    @magic_arguments.argument('--port', '-p', 
        help='The serial port connected to the Arduino')
    #   Redefine constants - allows #define to be used as parameters to
    #   the compile statement
        
    @magic_arguments.argument('--redefine', action='append', nargs = 2,
                help = '''#define constant to re-define.\n
                          Example: --redefine FREQUENCY 300\n
                          Spaces OK but must use double-quotes''')
    #   The Arduino board type
    @magic_arguments.argument('--board', '-b', 
        help='Arduino board type (uno, micro, etc.)')
    # Finally, the file name, which has no - or -- identifier.
    @magic_arguments.argument( 'filename', type=str,
        help='file to write')
    # Now we finally get on to our function
    def jarduino(self, line, cell):
        """Compiles, loads and runs the cell contents to the speccified board.Write the contents of the cell (an Arduino sketch) to the specified name and directory within
        the sketches subdirectory of the notebook.

        But first saves the cell contents to the specified directory. Default directory
        is sketches/<filename>.

	Example: jarduino mysketch
        - If not there, creates directory sketches
        - If not there, creates directory sketches/mysketch
        - Places the content of the cell in file sketches/mysketch/mysketch.ino
        """
        args = magic_arguments.parse_argstring(self.jarduino, line)
        # filename is all alone on the command line with no -x or --identifier
        # that's parsed out by default by the magic arguments parser because
        # we specified it above.
        # It it doesn't have .ino, we add it
        # It is also used (without the .ino, if it was specified) as the
        # directory to follow the Arduino IDE convention
        if args.filename:
            # Split it up to see if it has an extension of .ino
            filename, ext = os.path.splitext(args.filename)
            if ext != '.ino':
                filename = args.filename +'.ino'
                filedir = args.filename
            else: # filename has .ino at the end    
                # directory is the directory without .ino
                filedir = filename
                filename = args.filename
        else:
            print('Error: Filename required')
            return

        # By default, the Arduino IDE puts each sketch its own directory
        # with the same name as the file. So that's our default as well. 
        # Multiple sketches can be in the same directory, but they can't
        # share function names. That creates an error if we have two
        # independent sketches with their own void() and/or setup() functions.
        # Because multiple sketches in the same directory
        # get compiled as one big file. That's the Arduino IDE way.
        

                              
        # If no directory specified with -d or --dir on the command line,
        # use the filename as directory name. Same default as Arduino IDE.
        # If a path is specified, it's relative to the current path
        if args.dir is None:  #          
            # Just so our notebook isn't cluttered, we put all the sketch
            # directories under a subdirectory called "sketches"
            if not os.path.isdir('sketches'):
                print('Creating sketches directory for first time in notebook')
                os.mkdir('sketches')
            if not os.path.isdir(os.path.join('sketches', filedir)):
                os.mkdir(os.path.join('sketches', filedir))
                                 
            filename = os.path.join(os.getcwd(),'sketches',filedir, filename)
        else:
            # Is it an absolute path or a relative path?
            if os.path.isabs(args.dir):
                filename = os.path.join(args.dir, filename)
            else:
                filename =os.path.join(os.getcwd(),args.dir, filename)


        # Write out the file
        # The redefinefile() functions handles the #define substitutions
        if os.path.exists(filename):
            print('Overwriting', filename)
        else:
            print('Writing', filename)
        redefinefile(filename, args.redefine, cell)

                

        # Start the string for the Arduino command line options
        # Load to board or just compile and validate?
        if args.check:
            build_option = '--verify'
            print("-- check option: Compile only - will not attempt to load to board")                 
        else:
            build_option = '--upload'   # Full validate/compile/upload
            print("Build will upload to board if compile successful")

        # Figure out which port to use
    
        # Windows and Raspberry Pi port checks tell us if it's an Arduino.
        # Mac doesn't.
        if platform.system != 'Darwin': # If it's not a Mac...
            arduino_ports = [p.device for p in serial.tools.list_ports.comports()
                            if 'Arduino' in p.description]
            # If there are no Arduino ports found, only run if --check option enable 
            if not(arduino_ports): 
                if not(args.check):
                    print('No Arduino ports found. Run with -c to check and not upload')
                    return
            # Now figure out which port to use, or, if specified, 
            else:
                # If a port was specied , use it      
                if (args.port):
                    if args.port in arduino_ports:
                        arduino_port = args.port
                    else:
                        print('Port', args.port, 'not found. Available ports:', arduino_ports)
                        return
                else:
                    # If not, use the first one found
                    arduino_port = arduino_ports[0]
                    if len(arduino_ports) > 1:
                       print('Warning: Multiple Arduino ports found:', arduino_ports)
                print('Using arduino port', arduino_port)
                build_option +=' --port ' + arduino_port
        else: # ... but if we do have a Mac
            # If specified, check to see if at least it exists
            if args.port:
                serial_ports = [p.device for p in
                                serial.tools.list_ports.comports()]
                if args.port in serial_ports:
                    build_option += '--port ' + args.port
            else: #No port specified. Hope for the best.
                print('This is a Mac. No port specified. Hoping default Arduino IDE port works')

        # This triggers the Arduino build's verbose option. It's very verbose.
        if args.verbose:
            build_option += ' --verbose'
            
        # This is the board type. Because Arduino IDE uses --board.
        if args.board:
            build_option += ' --board arduino:avr:' + args.board    

        print('Starting Arduino build')
        pcmd = 'Arduino '+ build_option + ' ' +filename
        print('Command: ', pcmd)
        p = subprocess.Popen(pcmd, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE, shell=True)
 
        (output, err) = p.communicate()
 
        # Wait for command to terminate. And dump the output
        p_status = p.wait()
        print("Command output : ", output.decode('utf-8'))
        print("Command errors: ", err.decode('utf-8'))
        # Commented this out because it always gives 0 anyway.
        # print("Command exit status/return code : ", p_status)
        print("Done")
              

    # end jarduino ########################################


    ###############################
    # Magic: jardutil
    #
    # Runs utilities against the Arduino ports and code.
    #
    # It's a line magic (@line_magic) because it only cares about the parameters on the line
    # and not the rest of the cell.
    #
    # See comments for the arduino magic above for how all these weird @ things work for
    # defining parameters
    
    @line_magic
    
    # This sets us up to use the built-in Jupyter magics arguments toolkit
    @magic_arguments.magic_arguments()
    # We have an @magics_argument.argument line for each parameter.
    # We can have as many as we want.
    # The first arguments are flags - enabled or not.
    # 

    @magic_arguments.argument('--serialports', action='store_true',
        help='List available Arduino-connected ports')
    @magic_arguments.argument('--plot', type = int,
        help='Plot the number of points inside the notebook')
    @magic_arguments.argument('--stack', action='store_true',
        help='Stack instead of overlapping the plots')
    @magic_arguments.argument('--dirlist', '-d', 
        help='List all arduino sketch files in specified directory under sketches directory')
    @magic_arguments.argument('--plotext', type = str,
        help='User external plotter program')
    @magic_arguments.argument('--speed', '-s', type = str,
        help='Serial port speed')   
    @magic_arguments.argument('--port', '-p', type = str,
        help='The serial port connected to the Arduino')
    
  
    # Commented out --getprefs and --version because options don't
    # work on Windows arduino command
    #@magic_arguments.argument('--getprefs', '-g', action='store_true',
    #    help='Show current default preferences/settings of the Arduino IDE')
    #@magic_arguments.argument('--version', '-v', action='store_true',
    #    help='Show version of the installed Arduino IDE')
    #The next ones provide a parameter value

    # Now we finally get on to our function
    def jardutil(self, line):
        '''jardutil: utility for reading arduino configuration from system
        '''
        args = magic_arguments.parse_argstring(self.jardutil, line)

        build_option = ''
        
        if args.serialports:
            # On non-MAC systems, a serial port query identifies it as
            # Arduino connected.
            if platform.system() != 'Darwin':                
                print('Arduino ports on system:')
                print([p.description for p in serial.tools.list_ports.comports()
                       if 'Arduino' in p.description])
            else: # If it's a Mac...
                print('MAC system: Cannot identify Arduino ports. Listing all ports.')
                print([p.device for p in serial.tools.list_ports.comports()])

        if args.plot:
            plot_options = '--points ' + str(args.plot)
            if args.port:
                plot_options += ' --port ' + args.port
            if args.stack:
                plot_options += ' --stack'
            if args.speed:
                plot_options += ' --speed ' + args.speed
            
            #jardplotstatic((plot_options + ' --points ' +str(args.plot)).split())
            print('Plot options sent:', plot_options)
            jardplotstatic((plot_options).split())


        if args.plotext:
            runexternal(args.plotext)


## Commented out because the options don't work on Windows version of Arduino
## These are all things from the Arduino command line documentation!!!            
## If they work on Linux or Mac, we'll handle them. If not, we'll cut it out.
##            
##        if args.getprefs:
##            print('Current Arduino IDE preference settings:')
##            build_option += ' --get-pref'
##        if args.version:
##            build_option += ' --version'
##        if build_option != '':
##            p = subprocess.Popen(["Arduino",
##                 build_option], stdout=subprocess.PIPE,
##                 stderr=subprocess.PIPE, shell=True)
##
##            (output, err) = p.communicate()
## 
##            # Wait for command to terminate. And dump the output
##            p_status = p.wait()
##            print("Command output : ", output.decode('utf-8'))
##            print("Command errors: ", err.decode('utf-8'))


        if args.dirlist:
            adir = 'sketches'+ os.file.sep + args.dirlist
            print('Files in', adir,':')
            print(os.listdir(adir))



        
    #end jardutil ######################################
  

# Register the magics in the Ipython kernel

ip = get_ipython()
ip.register_magics(JarduinoMagics)



