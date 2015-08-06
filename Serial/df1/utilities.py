import re
from twisted.python import usage
from ConfigParser import SafeConfigParser

class Options(usage.Options):
    optParameters = [['config', 'c', './config.ini']]

#---------------------------------------------------------------------------#
# A custom class to read config files
#---------------------------------------------------------------------------#
class optionReader(object):
    def __init__(self):
        self.options = Options()
        self.config = SafeConfigParser()
        self.config.read([self.options['config']])

    def getEmail(self):
        sender = self.config.get('Email', 'From')
        recepient = self.config.get('Email', 'To')
        return (sender, recepient)

    def getFTPDirectories(self):
        localLog = self.config.get('FTP', 'localLogDir')
        remoteLog = self.config.get('FTP', 'remoteLogDir')
        return (localLog, remoteLog)

    def getRecipeDirectories(self):
        localDir = self.config.get('FTP', 'localRecipeDir')
        remoteDir = self.config.get('FTP', 'remoteRecipeDir')
        return (localDir, remoteDir)

    def getFTPTime(self):
        return self.config.getint('FTP', 'FTPTime')

    def getPLCVariables(self):
        return self.config.get('SLC', 'Parameters').split(',')

    def getOEETime(self):
        return self.config.getint('RS-232', 'OEETime')

    def getPLCAlarms(self):
        return self.config.get('SLC', 'Alarms').split(',')

    def getAlarmTime(self):
        return self.config.getfloat('RS-232', 'AlarmTime')

    def getFTPparms(self):
        host = self.config.get('FTP', 'host')
        port = self.config.getint('FTP', 'port')
        return (host, port)

    def getRS232parms(self):
        host = self.config.get('RS-232', 'host')
        baud = self.config.getint('RS-232', 'baudrate')
        return (host, baud)

    def getRS422Parms(self):
        host = self.config.get('RS-422', 'host')
        baud = self.config.getint('RS-422', 'baudrate')
        return (host, baud)
        
    
#---------------------------------------------------------------------------#
# Error Detection Functions
#---------------------------------------------------------------------------#
def __generate_crc16_table():
    ''' Generates a crc16 lookup table
    .. note:: This will only be generated once
    '''
    result = []
    for byte in range(256):
        crc = 0x0000
        for _ in range(8):
            if (byte ^ crc) & 0x0001:
                crc = (crc >> 1) ^ 0xa001
            else: crc >>= 1
            byte >>= 1
        result.append(crc)
    return result

__crc16_table = __generate_crc16_table()


def computeCRC(data, stx='\x03'):
    ''' Computes a crc16 on the passed in string. 
    
    :param data: The data to create a crc16 of
    :returns: The calculated CRC
    '''
    crc = 0x0000
    data += stx
    
    for a in data:
        idx = __crc16_table[(crc ^ ord(a)) & 0xff];
        crc = ((crc >> 8) & 0xff) ^ idx
    swapped = ((crc << 8) & 0xff00) | ((crc >> 8) & 0x00ff)
    return swapped


def checkCRC(data, check):
    ''' Checks if the data matches the passed in CRC
    :param data: The data to create a crc16 of
    :param check: The CRC to validate
    :returns: True if matched, False otherwise
    '''
    return computeCRC(data) == check

def flatten(items):
    flattened=[]
    if hasattr(items, '__iter__') and not isinstance(items, str):
        for item in items:
            if hasattr(item, '__iter__') and not isinstance(item, str):
                for subitem in flatten(item):
                    flattened.append(subitem)
            else:
                flattened.append(item)

    return flattened or items


class AddressObject(object):
    def __init__(self):
        self.size = 0
        self.fileNumber = 0
        self.fileType = 0
        self.eleNumber = 0
        self.bitNumber = None
        self.subElement = 0
        

def calcAddress(strAddress):
    
    error = -1;
    Address = AddressObject()

    FILE_TYPE = {
                 'S'  : 0x84,         #Status
                 'B'  : 0x85,         #Bit
                 'T'  : 0x86,         #Timer
                 'C'  : 0x87,         #Counter
                 'R'  : 0x88,         #Control
                 'N'  : 0x89,         #Integer
                 'F'  : 0x8A,         #Float
                 'O'  : 0x8B,         #Output
                 'I'  : 0x8C,         #Input
                 'ST' : 0x8D,         #String
                 'A'  : 0x8E,         #ASCII
                 'D'  : 0x8F,         #BCD
                 'MG' : 0x92,         #Message
                 'PD' : 0x93,         #PID
                 'PLS': 0x94          #Programmable Limit Switch
                }

    SUB_ELEMENTS = {
                   'PRE' : 1,
                   'ACC' : 2,
                   'EN'  : 15,
                   'TT'  : 14,
                   'DN'  : 13,
                   'CU'  : 15,
                   'CD'  : 14,
                   'OV'  : 12,
                   'UN'  : 11,
                   'UA'  : 10,
                   '0'   : 0,
                   '1'   : 1,
                   '2'   : 2,
                   '3'   : 3,
                   '4'   : 4,
                   '5'   : 5,
                   '6'   : 6,
                   '7'   : 7,
                   '8'   : 8}
                   
    ############################################################
    # 4 different regex patterns can be matched
    ############################################################
    mc = re.match("(?i)^\s*(?P<FileType>([SBCTRNFAIOL])|(ST)|(MG)|(PD)|(PLS))(?P<FileNumber>\d{1,3}):(?P<ElementNumber>\d{1,3})(/(?P<BitNumber>\d{1,4}))?\s*$", strAddress)
    if (mc == None):
        mc = re.match("(?i)^\s*(?P<FileType>[BN])(?P<FileNumber>\d{1,3})(/(?P<BitNumber>\d{1,4}))\s*$", strAddress)
        if (mc == None):
            mc = re.match("(?i)^\s*(?P<FileType>[CT])(?P<FileNumber>\d{1,3}):(?P<ElementNumber>\d{1,3})[.](?P<subElement>(ACC|PRE|EN|DN|TT|CU|CD|DN|OV|UN|UA))\s*$", strAddress)
            if (mc == None):
                mc = re.match("(?i)^\s*(?P<FileType>([IOS])):(?P<ElementNumber>\d{1,3})([.](?P<subElement>[0-7]))?(/(?P<BitNumber>\d{1,4}))?\s*$", strAddress)
                if (mc == None):
                    return Address
                
    ################################################
    # Get elements extracted from match patterns
    ################################################
    #fileType = ''
    #fileNumber = ''

    # Is it an I,O, or S address without a file number Type?
    if ('FileNumber' not in mc.groupdict()):
        # Is it an input or Output file?  
        if (mc.group('FileType').upper() == 'I'):
            Address.fileNumber = 1
        elif (mc.group('FileType').upper() == 'O'):
            Address.fileNumber = 0
        else:
            Address.fileNumber = 2
    # If it is not I, O, or S address without a file number Type
    else:
        Address.fileNumber = int(mc.group('FileNumber'))

    Address.fileType = FILE_TYPE[mc.group('FileType').upper()]
    
    ##############################################################
    # 2nd part should be the elementNumber
    ##############################################################
    #element = ''
    if ('BitNumber' in mc.groupdict()):
        if (mc.group('BitNumber') != None):
            Address.bitNumber = int(mc.group('BitNumber'))

    if ('ElementNumber' not in mc.groupdict()):
        if (Address.bitNumber < 16):
            Address.eleNumber = 0
        else:
            Address.eleNumber = Address.bitNumber >> 4
            Address.bitNumber = Address.bitNumber % 16
    else:
        Address.eleNumber = int(mc.group('ElementNumber'))
    
    ##############################################################
    # 3rd part should be the subElement if it exists
    ##############################################################
    #subelement = ''
    if ('subElement' in mc.groupdict()):
        if (mc.group('subElement') != None):
            Address.subElement = SUB_ELEMENTS[mc.group('subElement').upper()]

            # These subelements are bit level
            if (Address.subElement > 4):
                Address.bitNumber = Address.subElement
                Address.subElement = 0
        
    return Address
