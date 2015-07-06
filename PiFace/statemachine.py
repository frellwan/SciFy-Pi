# StateMachine/State.py
# A State has an operation, and can be moved
# into the next State given an Input:

from pifacecad.tools.scanf import *


class State:
    def run(self):
        assert 0, "run not implemented"
    def next(self, input):
        assert 0, "next not implemented"

# StateMachine/StateMachine.py
# Takes a list of Inputs to move from State to
# State using a template method.

class StateMachine:
    def __init__(self, initialState):
        self.currentState = initialState
        self.currentState.run()
    # Template method:
    def runAll(self, inputs):
        for i in inputs:
            print(i)
            self.currentState = self.currentState.next(i)
            self.currentState.run()

class Waiting(State):
    def __init__(self, cad, SM):
        self.cad = cad
        self.SM = SM
    
    def run(self):
        #print("Waiting for key press")
        self.cad.lcd.display_off()
        return (self.SM.waiting,)

    def next(self, event):
        return (self.SM.menu, 0)

class Menu(State):
    def __init__(self, cad, SM):
        #self.cad = cad
        self.section = 0
        self.cad = cad
        self.SM = SM
        self.parser = SM.parser
        self.sections = []
        
    def run(self, section=None):
        #print("Menu: showing config sections: ", self.section)
        if (section != None):
            self.section = section
        self.sections = self.parser.sections()
        self.cad.lcd.display_on()
        self.cad.lcd.cursor_off()
        self.cad.lcd.blink_off()
        self.cad.lcd.clear()
        self.cad.lcd.write("MENU\n")        
        self.cad.lcd.write("[{}]".format(self.sections[self.section]))
        #self.cad.lcd.cursor_off()
    def next(self, event):
        next_state = [(self.SM.menu,),
                      (self.SM.menu,),
                      (self.SM.menu,),
                      (self.SM.menu,),
                      (self.SM.menu,),
                      (self.SM.sections, (self.sections[self.section], 0)),
                      (self.SM.menu,),
                      (self.SM.menu,)]
                      
        if (event == 0 or event == 6):
            if (self.section == 0):
                self.section = len(self.parser.sections())-1
            else:
                self.section -= 1

        elif (event == 1 or event == 7):
            if(self.section == len(self.parser.sections())-1):
                self.section = 0
            else:
               self.section += 1

        return next_state[event]

class Sections(State):
    def __init__(self, cad, SM):
        self.cad = cad
        self.SM = SM
        self.parser = SM.parser
        self.section = ''
        self.index = 0
        self.options = []

    def run(self, section=None):
        #print("Sections: showing options for current section:", self.section)
        if (section != None):
            self.section = section[0]
            self.index = section[1]
        self.options = self.parser.options(self.section)
        self.cad.lcd.clear()
        self.cad.lcd.write("[{}]\n".format(self.section))
        self.cad.lcd.write("[{}]".format(self.options[self.index]))
        #self.cad.lcd.cursor_off()

    def next(self, event):
        next_state = [(self.SM.sections, ),
                      (self.SM.sections, ),
                      (self.SM.sections, ),
                      (self.SM.sections, ),
                      (self.SM.menu,),
                      (self.SM.options, (self.section, self.options[self.index], 0)),
                      (self.SM.sections, ),
                      (self.SM.sections, )]

        if (event == 0 or event == 6):
            if (self.index == 0):
                self.index = len(self.options)-1
            else:
                self.index -= 1

        elif (event == 1 or event == 7):
            if(self.index == len(self.options)-1):
                self.index = 0
            else:
               self.index += 1

        return next_state[event]
    
class Options(State):
    def __init__(self, cad, SM):
        self.cad = cad
        self.SM = SM
        self.parser = SM.parser
        self.index = 0
        self.subOption = ['']
        self.section = ''
        self.option = ''

    def run(self, arg_tuple=None):
        #print("Options: showing items for current option: ", self.items[self.item])
        if (arg_tuple != None):
            self.section = arg_tuple[0]
            self.option = arg_tuple[1]
            self.subOption = self.parser.get(self.section,self.option).split('\n')
            self.index = arg_tuple[2]
            
        self.cad.lcd.clear()
        self.cad.lcd.write("[{}]\n".format(self.option))        
        self.cad.lcd.write("[{}]".format(self.subOption[self.index]))
        #self.cad.lcd.cursor_off()

    def next(self, event):
        next_state = [(self.SM.options, ),
                      (self.SM.options, ),
                      (self.SM.options, ),
                      (self.SM.options, ),
                      (self.SM.sections, ),
                      (self.SM.editing, (self.section, self.option, self.index, self.parser.get(self.section, self.option).split('\n'))),
                      (self.SM.options, ),
                      (self.SM.options, )]

        if (event == 0 or event == 6):
            if (self.index == 0):
                self.index = len(self.subOption)-1
            else:
                self.index -= 1

        elif (event == 1 or event == 7):
            if(self.index == len(self.subOption)-1):
                self.index = 0
            else:
                self.index += 1
        
        return next_state[event]

class Editing(State):
    def __init__(self, cad, SM):
        self.cad = cad
        self.SM = SM
        self.parser = SM.parser
        self.section = ''
        self.subOption = ''
        self.subOptions = []
        self.index = 0
        self.col = 0
        self. row = 1

    def run(self, arg_tuple = None):
        #print("Editing: allowing edits to current option", option_item)
        if (arg_tuple != None):
            self.section = arg_tuple[0]
            self.subOption = arg_tuple[1]
            self.index = arg_tuple[2]
            self.subOptions = arg_tuple[3]
            self.col = 0
            self. row = 1
        self.cad.lcd.cursor_on()
        self.cad.lcd.blink_off()
        self.cad.lcd.clear()
        self.cad.lcd.write("[{}]\n".format(self.subOption))        
        self.cad.lcd.write("{}".format(self.subOptions[self.index]))
        self.cad.lcd.set_cursor(self.col, self.row)
        self.cad.lcd.see_cursor()

    def next(self, event):
        next_state = [(self.SM.scanning, (self.section,self.subOption,self.subOptions, self.index, ValueSelectString("%C%r", None))),
                      (self.SM.scanning, (self.section,self.subOption,self.subOptions, self.index, ValueSelectString("%c%r", None))),
                      (self.SM.scanning, (self.section,self.subOption,self.subOptions, self.index, ValueSelectString("%i%r", None))),
                      (self.SM.scanning, (self.section,self.subOption,self.subOptions, self.index, ValueSelectString("%.%r", None))),
                      (self.SM.options,(self.section, self.subOption, 0)),
                      (self.SM.options,(self.section, self.subOption, 0)),
                      (self.SM.editing,),
                      (self.SM.editing,)]


        if (event == 7):
            self.col, self.row = self.cad.lcd.get_cursor()
            if (self.col < len(self.subOptions[self.index])):
                self.col += 1
            self.cad.lcd.set_cursor(self.col, self.row)

        elif (event == 6):
            self.col, self.ow = self.cad.lcd.get_cursor()
            if (self.col > 0):
                self.col -= 1
            self.cad.lcd.set_cursor(self.col, self.row)

        elif (event == 5):
            #write param to config file
            self.subOptions[self.index] = self.subOptions[self.index]
            self.parser[self.section][self.subOption] = ('\n').join(self.subOptions)
            with open(self.SM.configFile, 'w') as iniFile:
                self.parser.write(iniFile)
    
        return next_state[event]

class Scanning(State):
    def __init__(self, cad, SM):
        self.cad = cad
        self.SM = SM
        self.parser = SM.parser
        self.section = ''
        self.option = ''
        self.subOptions = []
        self.col = 0
        self.item = ''
        self.option = ''

    def run(self, arg_tuple = None):
        #print("Editing: allowing edits to current option", item)
        if (arg_tuple != None):
            self.section = arg_tuple[0]
            self.option = arg_tuple[1]
            self.subOptions = arg_tuple[2]
            self.index = arg_tuple[3]
            self.display_string = arg_tuple[4]
            self.new_options = self.subOptions

        self.start_offset = self.cad.lcd.get_cursor()
        self.cad.lcd.blink_on()
        self.cad.lcd.display_on()
        self.cad.lcd.clear()
        self.cad.lcd.write("[{}]\n".format(self.option))        
        self.cad.lcd.write("{}".format(self.new_options[self.index]))
        self.cad.lcd.set_cursor(self.start_offset[0], self.start_offset[1])

    def next(self, event):
        next_state = [(self.SM.scanning,),
                      (self.SM.scanning,),
                      (self.SM.scanning,),
                      (self.SM.scanning,),
                      (self.SM.editing,(self.section, self.option, self.index, self.subOptions)),
                      (self.SM.editing,(self.section, self.option, self.index, self.new_options)),
                      (self.SM.scanning,),
                      (self.SM.scanning,)]

        #self.cad.lcd.clear()
        self.cad.lcd.write(str(self.display_string))
        # set the cursor to a sensible position
        try:
            first_value_select_index = \
                self.display_string.instanceindex(ValueSelect)
        except TypeError:
            # nothing to select, show the string and return
            self.cad.lcd.display_on()
            return self.display_string.selected_values
        else:
            col = first_value_select_index + self.start_offset[0]
            row = self.start_offset[1]
            self.cad.lcd.set_cursor(col, row)
            self.cad.lcd.display_on()


        #Increment Selection
        if (event == 7):
            col, row = self.cad.lcd.get_cursor()
            value_select = self.display_string.value_at(col-self.start_offset[0])
            value_select.increment_value()
            string = str(value_select.value).ljust(value_select.longest_len)
            self.new_options[self.index] = self.new_options[self.index][:col] + string + self.new_options[self.index][col+1:]

        #Decrement Selection
        elif (event == 6):
            col, row = self.cad.lcd.get_cursor()
            value_select = self.display_string.value_at(col-self.start_offset[0])
            value_select.decrement_value()
            string = str(value_select.value).ljust(value_select.longest_len)
            self.new_options[self.index] = self.new_options[self.index][:col] + string + self.new_options[self.index][col+1:]
 
        #def accept(self, event):
        elif (event == 5):
            #self.item = self.new_item
            pass

        return next_state[event]
