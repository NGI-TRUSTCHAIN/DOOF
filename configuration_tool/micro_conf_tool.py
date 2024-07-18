#   SPDX-License-Identifier: Apache-2.0

# author:   graz
# company:  ecosteer
# date:     31/05/2024
# ver:      2.1

# ver 2.1
# improved html

# ver 2.0
# added option "Brightness" (see "bright" within the access point configuration file)

# Changes 1.9.3 by geobud: 
# - access point ssid and password are based on MAC address 

#import pdb

# set MODE to 'test' if you want to run webbo without deploying it to an ESP32
# if MODE is set to 'test' the package "machine" will not be imported
# and the list of avalable access points will be populated with ['A', 'B', 'C']

#MODE='test'
MODE='RUN'

TEST_IP='192.168.200.18'   # used for test
TEST_PORT=2783            # used for test


if MODE!='test':
  import network
try:
  import usocket as socket
except:
  import socket
import json

if MODE=='RUN':
  import machine 

class htmlCodes:
    def __init__(self):
        self.__codes_E2: list = [
            [128,'%80','%E2%82%AC'],
            [130,'%82','%E2%80%9A'],
            [132,'%84','%E2%80%9E'],
            [133,'%85','%E2%80%A6'],
            [134,'%86','%E2%80%A0'],
            [135,'%87','%E2%80%A1'],
            [137,'%89','%E2%80%B0'],
            [139,'%8B','%E2%80%B9'],
            [145,'%91','%E2%80%98'],
            [146,'%92','%E2%80%99'],
            [147,'%93','%E2%80%9C'],
            [148,'%94','%E2%80%9D'],
            [149,'%95','%E2%80%A2'],
            [150,'%96','%E2%80%93'],
            [151,'%97','%E2%80%94'],
            [153,'%99','%E2%84'],       # try to match the longer sequences, first
            [155,'%9B','%E2%80']        # try to match the longer sequences, first
        ]
        
        self.__codes_C2: list = [
            [144,'%90','%C2%90'],
            [160,'%A0','%C2%A0'],
            [161,'%A1','%C2%A1'],
            [162,'%A2','%C2%A2'],
            [163,'%A3','%C2%A3'],
            [164,'%A4','%C2%A4'],
            [165,'%A5','%C2%A5'],
            [166,'%A6','%C2%A6'],
            [167,'%A7','%C2%A7'],
            [168,'%A8','%C2%A8'],
            [169,'%A9','%C2%A9'],
            [170,'%AA','%C2%AA'],
            [171,'%AB','%C2%AB'],
            [172,'%AC','%C2%AC'],
            [173,'%AD','%C2%AD'],
            [174,'%AE','%C2%AE'],
            [175,'%AF','%C2%AF'],
            [176,'%B0','%C2%B0'],
            [177,'%B1','%C2%B1'],
            [178,'%B2','%C2%B2'],
            [179,'%B3','%C2%B3'],
            [180,'%B4','%C2%B4'],
            [181,'%B5','%C2%B5'],
            [182,'%B6','%C2%B6'],
            [183,'%B7','%C2%B7'],
            [184,'%B8','%C2%B8'],
            [185,'%B9','%C2%B9'],
            [186,'%BA','%C2%BA'],
            [187,'%BB','%C2%BB'],
            [188,'%BC','%C2%BC'],
            [189,'%BD','%C2%BD'],
            [190,'%BE','%C2%BE'],
            [191,'%BF','%C2%BF']
        ]

        self.__codes_C3: list = [
            [192,'%C0','%C3%80'],
            [193,'%C1','%C3%81'],
            [194,'%C2','%C3%82'],
            [195,'%C3','%C3%83'],
            [196,'%C4','%C3%84'],
            [197,'%C5','%C3%85'],
            [198,'%C6','%C3%86'],
            [199,'%C7','%C3%87'],
            [200,'%C8','%C3%88'],
            [201,'%C9','%C3%89'],
            [202,'%CA','%C3%8A'],
            [203,'%CB','%C3%8B'],
            [204,'%CC','%C3%8C'],
            [205,'%CD','%C3%8D'],
            [206,'%CE','%C3%8E'],
            [207,'%CF','%C3%8F'],
            [208,'%D0','%C3%90'],
            [209,'%D1','%C3%91'],
            [210,'%D2','%C3%92'],
            [211,'%D3','%C3%93'],
            [212,'%D4','%C3%94'],
            [213,'%D5','%C3%95'],
            [214,'%D6','%C3%96'],
            [215,'%D7','%C3%97'],
            [216,'%D8','%C3%98'],
            [217,'%D9','%C3%99'],
            [218,'%DA','%C3%9A'],
            [219,'%DB','%C3%9B'],
            [220,'%DC','%C3%9C'],
            [221,'%DD','%C3%9D'],
            [222,'%DE','%C3%9E'],
            [223,'%DF','%C3%9F'],
            [224,'%E0','%C3%A0'],
            [225,'%E1','%C3%A1'],
            [226,'%E2','%C3%A2'],
            [227,'%E3','%C3%A3'],
            [228,'%E4','%C3%A4'],
            [229,'%E5','%C3%A5'],
            [230,'%E6','%C3%A6'],
            [231,'%E7','%C3%A7'],
            [232,'%E8','%C3%A8'],
            [233,'%E9','%C3%A9'],
            [234,'%EA','%C3%AA'],
            [235,'%EB','%C3%AB'],
            [236,'%EC','%C3%AC'],
            [237,'%ED','%C3%AD'],
            [238,'%EE','%C3%AE'],
            [239,'%EF','%C3%AF'],
            [240,'%F0','%C3%B0'],
            [241,'%F1','%C3%B1'],
            [242,'%F2','%C3%B2'],
            [243,'%F3','%C3%B3'],
            [244,'%F4','%C3%B4'],
            [245,'%F5','%C3%B5'],
            [246,'%F6','%C3%B6'],
            [247,'%F7','%C3%B7'],
            [248,'%F8','%C3%B8'],
            [249,'%F9','%C3%B9'],
            [250,'%FA','%C3%BA'],
            [251,'%FB','%C3%BB'],
            [252,'%FC','%C3%BC'],
            [253,'%FD','%C3%BD'],
            [254,'%FE','%C3%BE'],
            [255,'%FF','%C3%BF']
        ]

        self.__codes_C5: list = [
            [138,'%8A','%C5%A0'],
            [140,'%8C','%C5%92'],
            [141,'%8D','%C5%8D'],
            [142,'%8E','%C5%BD'],
            [154,'%9A','%C5%A1'],
            [156,'%9C','%C5%93'],
            [158,'%9E','%C5%BE'],
            [159,'%9F','%C5%B8']
        ]

        self.__codes_C6: list = [
            [131,'%83','%C6%92']
        ]

        self.__codes_CB: list = [
            [136,'%88','%CB%86'],
            [152,'%98','%CB%9C']
        ]

        # please note that self.__codes is not used
        self.__codes: list = [
            #   see url: https://www.w3schools.com/tags/ref_urlencode.ASP
            #   see url: https://www.ascii-code.com/
            #   ascii code dec, ascii code hex, utf-8
            #   ascii control chars
            [0,'%00','%00'],
            [1,'%01','%01'],
            [2,'%02','%02'],
            [3,'%03','%03'],
            [4,'%04','%04'],
            [5,'%05','%05'],
            [6,'%06','%06'],
            [7,'%07','%07'],
            [8,'%08','%08'],
            [9,'%09','%09'],
            [10,'%0A','%0A'],
            [11,'%0B','%0B'],
            [12,'%0C','%0C'],
            [13,'%0D','%0D'],
            [14,'%0E','%0E'],
            [15,'%0F','%0F'],
            [16,'%10','%10'],
            [17,'%11','%11'],
            [18,'%12','%12'],
            [19,'%13','%13'],
            #   printable ascii chars
            [20,'%14','%14'],
            [21,'%15','%15'],
            [22,'%16','%16'],
            [23,'%17','%17'],
            [24,'%18','%18'],
            [25,'%19','%19'],
            [26,'%1A','%1A'],
            [27,'%1B','%1B'],
            [28,'%1C','%1C'],
            [29,'%1D','%1D'],
            [30,'%1E','%1E'],
            [31,'%1F','%1F'],
            [32,'%20','%20'],
            [33,'%21','%21'],
            [34,'%22','%22'],
            [35,'%23','%23'],
            [36,'%24','%24'],
            [37,'%25','%25'],
            [38,'%26','%26'],
            [39,'%27','%27'],
            [40,'%28','%28'],
            [41,'%29','%29'],
            [42,'%2A','%2A'],
            [43,'%2B','%2B'],
            [44,'%2C','%2C'],
            [45,'%2D','%2D'],
            [46,'%2E','%2E'],
            [47,'%2F','%2F'],
            [48,'%30','%30'],
            [49,'%31','%31'],
            [50,'%32','%32'],
            [51,'%33','%33'],
            [52,'%34','%34'],
            [53,'%35','%35'],
            [54,'%36','%36'],
            [55,'%37','%37'],
            [56,'%38','%38'],
            [57,'%39','%39'],
            [58,'%3A','%3A'],
            [59,'%3B','%3B'],
            [60,'%3C','%3C'],
            [61,'%3D','%3D'],
            [62,'%3E','%3E'],
            [63,'%3F','%3F'],
            [64,'%40','%40'],
            [65,'%41','%41'],
            [66,'%42','%42'],
            [67,'%43','%43'],
            [68,'%44','%44'],
            [69,'%45','%45'],
            [70,'%46','%46'],
            [71,'%47','%47'],
            [72,'%48','%48'],
            [73,'%49','%49'],
            [74,'%4A','%4A'],
            [75,'%4B','%4B'],
            [76,'%4C','%4C'],
            [77,'%4D','%4D'],
            [78,'%4E','%4E'],
            [79,'%4F','%4F'],
            [80,'%50','%50'],
            [81,'%51','%51'],
            [82,'%52','%52'],
            [83,'%53','%53'],
            [84,'%54','%54'],
            [85,'%55','%55'],
            [86,'%56','%56'],
            [87,'%57','%57'],
            [88,'%58','%58'],
            [89,'%59','%59'],
            [90,'%5A','%5A'],
            [91,'%5B','%5B'],
            [92,'%5C','%5C'],
            [93,'%5D','%5D'],
            [94,'%5E','%5E'],
            [95,'%5F','%5F'],
            [96,'%60','%60'],
            [97,'%61','%61'],
            [98,'%62','%62'],
            [99,'%63','%63'],
            [100,'%64','%64'],
            [101,'%65','%65'],
            [102,'%66','%66'],
            [103,'%67','%67'],
            [104,'%68','%68'],
            [105,'%69','%69'],
            [106,'%6A','%6A'],
            [107,'%6B','%6B'],
            [108,'%6C','%6C'],
            [109,'%6D','%6D'],
            [110,'%6E','%6E'],
            [111,'%6F','%6F'],
            [112,'%70','%70'],
            [113,'%71','%71'],
            [114,'%72','%72'],
            [115,'%73','%73'],
            [116,'%74','%74'],
            [117,'%75','%75'],
            [118,'%76','%76'],
            [119,'%77','%77'],
            [120,'%78','%78'],
            [121,'%79','%79'],
            [122,'%7A','%7A'],
            [123,'%7B','%7B'],
            [124,'%7C','%7C'],
            [125,'%7D','%7D'],
            [126,'%7E','%7E'],
            [127,'%7F','%7F'],
            #   extended ASCII codes
            [128,'%80','%E2%82%AC'],
            [129,'%81','%81'],
            [130,'%82','%E2%80%9A'],
            [131,'%83','%C6%92'],
            [132,'%84','%E2%80%9E'],
            [133,'%85','%E2%80%A6'],
            [134,'%86','%E2%80%A0'],
            [135,'%87','%E2%80%A1'],
            [136,'%88','%CB%86'],
            [137,'%89','%E2%80%B0'],
            [138,'%8A','%C5%A0'],
            [139,'%8B','%E2%80%B9'],
            [140,'%8C','%C5%92'],
            [141,'%8D','%C5%8D'],
            [142,'%8E','%C5%BD'],
            [143,'%8F','%8F'],
            [144,'%90','%C2%90'],
            [145,'%91','%E2%80%98'],
            [146,'%92','%E2%80%99'],
            [147,'%93','%E2%80%9C'],
            [148,'%94','%E2%80%9D'],
            [149,'%95','%E2%80%A2'],
            [150,'%96','%E2%80%93'],
            [151,'%97','%E2%80%94'],
            [152,'%98','%CB%9C'],
            [153,'%99','%E2%84'],
            [154,'%9A','%C5%A1'],
            [155,'%9B','%E2%80'],
            [156,'%9C','%C5%93'],
            [157,'%9D','%9D'],
            [158,'%9E','%C5%BE'],
            [159,'%9F','%C5%B8'],
            [160,'%A0','%C2%A0'],
            [161,'%A1','%C2%A1'],
            [162,'%A2','%C2%A2'],
            [163,'%A3','%C2%A3'],
            [164,'%A4','%C2%A4'],
            [165,'%A5','%C2%A5'],
            [166,'%A6','%C2%A6'],
            [167,'%A7','%C2%A7'],
            [168,'%A8','%C2%A8'],
            [169,'%A9','%C2%A9'],
            [170,'%AA','%C2%AA'],
            [171,'%AB','%C2%AB'],
            [172,'%AC','%C2%AC'],
            [173,'%AD','%C2%AD'],
            [174,'%AE','%C2%AE'],
            [175,'%AF','%C2%AF'],
            [176,'%B0','%C2%B0'],
            [177,'%B1','%C2%B1'],
            [178,'%B2','%C2%B2'],
            [179,'%B3','%C2%B3'],
            [180,'%B4','%C2%B4'],
            [181,'%B5','%C2%B5'],
            [182,'%B6','%C2%B6'],
            [183,'%B7','%C2%B7'],
            [184,'%B8','%C2%B8'],
            [185,'%B9','%C2%B9'],
            [186,'%BA','%C2%BA'],
            [187,'%BB','%C2%BB'],
            [188,'%BC','%C2%BC'],
            [189,'%BD','%C2%BD'],
            [190,'%BE','%C2%BE'],
            [191,'%BF','%C2%BF'],
            [192,'%C0','%C3%80'],
            [193,'%C1','%C3%81'],
            [194,'%C2','%C3%82'],
            [195,'%C3','%C3%83'],
            [196,'%C4','%C3%84'],
            [197,'%C5','%C3%85'],
            [198,'%C6','%C3%86'],
            [199,'%C7','%C3%87'],
            [200,'%C8','%C3%88'],
            [201,'%C9','%C3%89'],
            [202,'%CA','%C3%8A'],
            [203,'%CB','%C3%8B'],
            [204,'%CC','%C3%8C'],
            [205,'%CD','%C3%8D'],
            [206,'%CE','%C3%8E'],
            [207,'%CF','%C3%8F'],
            [208,'%D0','%C3%90'],
            [209,'%D1','%C3%91'],
            [210,'%D2','%C3%92'],
            [211,'%D3','%C3%93'],
            [212,'%D4','%C3%94'],
            [213,'%D5','%C3%95'],
            [214,'%D6','%C3%96'],
            [215,'%D7','%C3%97'],
            [216,'%D8','%C3%98'],
            [217,'%D9','%C3%99'],
            [218,'%DA','%C3%9A'],
            [219,'%DB','%C3%9B'],
            [220,'%DC','%C3%9C'],
            [221,'%DD','%C3%9D'],
            [222,'%DE','%C3%9E'],
            [223,'%DF','%C3%9F'],
            [224,'%E0','%C3%A0'],
            [225,'%E1','%C3%A1'],
            [226,'%E2','%C3%A2'],
            [227,'%E3','%C3%A3'],
            [228,'%E4','%C3%A4'],
            [229,'%E5','%C3%A5'],
            [230,'%E6','%C3%A6'],
            [231,'%E7','%C3%A7'],
            [232,'%E8','%C3%A8'],
            [233,'%E9','%C3%A9'],
            [234,'%EA','%C3%AA'],
            [235,'%EB','%C3%AB'],
            [236,'%EC','%C3%AC'],
            [237,'%ED','%C3%AD'],
            [238,'%EE','%C3%AE'],
            [239,'%EF','%C3%AF'],
            [240,'%F0','%C3%B0'],
            [241,'%F1','%C3%B1'],
            [242,'%F2','%C3%B2'],
            [243,'%F3','%C3%B3'],
            [244,'%F4','%C3%B4'],
            [245,'%F5','%C3%B5'],
            [246,'%F6','%C3%B6'],
            [247,'%F7','%C3%B7'],
            [248,'%F8','%C3%B8'],
            [249,'%F9','%C3%B9'],
            [250,'%FA','%C3%BA'],
            [251,'%FB','%C3%BB'],
            [252,'%FC','%C3%BC'],
            [253,'%FD','%C3%BD'],
            [254,'%FE','%C3%BE'],
            [255,'%FF','%C3%BF']
        ]

    def __decode(self, codes: list, querystring: str):
        #   return the ascii ode of the decoded character, the html code and the number of digits used to encode the char 
        #   suppose that the querystring starts with %E2%82%AC, the number of digist will be 9
        for c in codes:
            l = len(c[2])
            if c[2]==querystring[0:l]:
                rend = '&#' + str(c[0]) + ';'   # rend is assigned to the html encoding "&#%ascii" e.g. &#128
                #return chr(c[0]),rend,l
                return c[0],rend,l
        return 0,'',-1


    
    def decode (self, querystring: str) -> dict:
        #decoded: str = ''   #   the complete string, decoded
        decoded: list = []   #   the complete string, decoded
        encoded: str = ''   #   the string holding the html encoded string, this is formed using the rend(s)
        #next: str = ''     #   the character that will be appended to the decoded string
        next: int = 0       #   the ascii code of the character that will be appended to the decoded string (list)
        i: int = 0          #   current index of the querystring to be checked for decoding
        step: int = 0       #   step used to increment i (this depend on the specific utf-8 sequence)
        while i < len(querystring):
            step = 1
            c = querystring[i]
            next = ord(c)
            rend = c
            if c == '+':
                next = 32
                rend = ' '
            elif c == '%':                            #   this is utf-8 character
                enc: str = querystring[i+1:i+3]     #   get the next two digits
                #   C2 C3 C5 C6 CB E2
                if      enc == 'C2':
                    next, rend, step = self.__decode(self.__codes_C2, querystring[i:])
                elif    enc == 'C3':
                    next, rend, step = self.__decode(self.__codes_C3, querystring[i:])
                elif    enc == 'C5':
                    next, rend, step = self.__decode(self.__codes_C5, querystring[i:])
                elif    enc == 'C6':
                    next, rend, step = self.__decode(self.__codes_C6, querystring[i:])
                elif    enc == 'CB':
                    next, rend, step = self.__decode(self.__codes_CB, querystring[i:])
                elif    enc == 'E2':
                    next, rend, step = self.__decode(self.__codes_E2, querystring[i:])
                else:
                    #pdb.set_trace()
                    #   this is an hex that has to be converted into a char (ASCI)
                    hex: str = '0x' + enc
                    ascii = int(hex,16)                
                    #next = chr(ascii)
                    next = ascii
                    rend = '&#' + str(ascii) + ';'
                    step = 3
                

            if (step < 0):
                return {'value': [], 'rend' : '', 'err': 1}
            
            #decoded = decoded + next
            decoded.append(next)
            encoded = encoded + rend
            i=i+step
        return { 'value': decoded, 'rend': encoded, 'err': 0 }

        


class Webbo:
  def __init__(self, options: dict):
    self.__configuration_parameters = options['configuration_parameters']
    self.__writer = None
    self.__ip = '127.0.0.1'
    self.__port = 80
    if 'writer' in options:
      self.__writer = options['writer']
    if 'ip' in options:
      self.__ip = options['ip']
    if 'port' in options:
       self.__port = int(options['port'])
    self.__connection = None
    self.__on_write_failure = False
    self.__hc = htmlCodes()


  def on_write(self) -> bool:
    if self.__writer == None:
      return True
    ret = False
    try:
      ret = self.__writer(self.__configuration_parameters)
    except:
      return False
    return ret


  def send_response(self, response: str) -> bool:
    if self.__connection == None:
      return False
    
    # sends the response to the client
    data = response.encode('utf-8')
    total_sent = 0
    while total_sent < len(data):
      sent = self.__connection.send(data[total_sent:])
      if sent == 0:
          #raise RuntimeError("Socket connection broken")
          return False
      total_sent += sent  
    return True


  def get_request_url(self,request: bytes) -> str:
    # this method extracts the resource from the HTTP request
    # the resource (URL) can be '/' or other, please see the resources processed in the
    # loop
    sreq = request.decode('utf-8')
    HTTP_method = 'GET '
    idx: int = sreq.find(HTTP_method)
    if idx < 0:
      # only GET request are supported
      return ''
    page = sreq[(idx+len(HTTP_method)):]
    idx = page.find(' ')  # find the first ' ' after the resource (URL)
    return page[:idx]
  
  # CONF PARS: /?ssid=MK_Guest&pwd=%E2%82%ACdf%C4%9F&modeop=CONNECTED
  # %E2%82%AC df %C4%9F

  def urldecode(self, v: str) -> dict:
    o: dict = self.__hc.decode(v)
    #   o holds 'value' and 'rend'
    return o
    

    
  def form_data(self, request: str) -> bool:
    """
      try to extract the form values
      if the values have been assigned then this fun rets True,
      False otherwise
    """
    #pdb.set_trace()
    sreq = request + '&'    
    for parameter in self.__configuration_parameters:
      pidx = sreq.find(parameter['id'])
      if pidx < 0:
        # one parameter is missing
        return False
      # the parameter has been found, now retrieve the value
      r = sreq[pidx+len(parameter['id'])+1:] # +1 just because the syntax is parameter=
      # now find the folowing '&'
      ampidx = r.find('&')
      if ampidx < 0:
        ampidx = r.find(' ')
        if ampidx < 0:
          return False
      try:
        #print(r[0:ampidx])
        #parameter['value'] = self.urldecode(r[0:ampidx])
        o: dict = self.urldecode(r[0:ampidx])
        if o['err'] == 0:
            parameter['value'] = o['value']
            parameter['rend'] = o['rend']
      except:
        return False

    return True # this will have to return ret_val

  def style(self) -> str:
    meta:   str = '<meta name="viewport" content="width=device-width, initial-scale=0.8">\r\n'
    box:    str = '.box { display: grid; grid-template-columns: 1fr 3fr; grid-gap: 10px; }\r\n'
    #style:  str = 'span { font-size: 3vw; font-family: Arial, sans-serif;}\r\ninput { font-size: 3vw; font-family: Arial, sans-serif;}\r\nselect { font-size: 3vw; font-family: Arial, sans-serif;}\r\nlabel { font-size: 3vw; font-family: Arial, sans-serif;}\r\nbutton { font-size: 3vw; font-family: Arial, sans-serif;}\r\n'
    style:  str = 'span, input, select, label, button { font-size: 1.3rem; font-family: Arial, sans-serif;}\r\n'
    style = style + '@media (min-width: 500px) {span, input, select, label, button {font-size: 1.5rem;}}\r\n'
    style = style + 'body { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; padding-left: 2rem;}\r\n'
    style = style + '.content { max-width: 500px; width: 100%; align-self: center;}\r\n'
    style = style + 'h1 { margin-bottom: 2rem; align-self: center;}\r\n'
    style = style + "footer { margin-top: 1rem; align-self: center; font-size: 1.0rem; font-family: Verdana, sans-serif;}\r\n"
    return  meta + '<style>' + box + style + '</style>'
  

  def page_configuration(self) -> str:
    """
      return the main configuration page
    """
    #   see ref https://www.w3schools.com/tags/ref_urlencode.ASP
    html_form: str = '<form accept-charset="utf-8"><div class="box is-inline-grid">'
    #html_form: str = '<form accept-charset="ansi"><div class="box is-inline-grid">'
    # please note that the label property is not used, yet
    input: str
    for p in self.__configuration_parameters:
      if 'options' in p:
        # this has to be a drop down list
        input = '<select name="' + p['id'] + '">'
        for v in p['options']:
          if v == p['value']:
            input = input + '<option value="' + v + '" selected>' + v + '</option>'
          else:
            input = input + '<option value="' + v + '">' + v + '</option>'
        input = input + '</select>'
      else:
        #input = '<input type="text" name="' + p['id'] + '" value="' + p['value'] + '">'
         input = '<input type="text" name="' + p['id'] + '" value="' + p['rend'] + '">'
      # here the two divs (same line in the grid) are created  
      html_form = html_form + '<div><label for="' + p['id'] + ':">' + p['label'] + '</label></div><div>' + input + '</div>'
    html_form = html_form + '<input type="submit" value="OK"></div></form>'

    
    html: str = '<html><head>'
    html = html + self.style()
    html = html + '</head><body><h1>Configuration</h1>'
    html = html + '<div class="content">'
    if self.__on_write_failure == True:
      html = html + '<span>The configuration parameters could not be stored. Please check and repeat the process</span>'
    html = html + html_form
    html = html + '</div>'
    html = html + '<footer><small>&copy; Copyright 2024, Ecosteer Srl</small></footer>'
    html = html + '</body></html>'

    return html

  def page_configuration_check(self) -> str:
    html: str = '<html><head>'
    html = html + self.style()
    html = html + '</head><body><h1>Configuration OK?</h1>'
    html = html + '<div class="content">'
    html = html + '<div class="box is-inline-grid">'

    for p in self.__configuration_parameters:
      #html = html + '<div><span>' + p['label'] + '</span></div><div><span>' + p['value'] + '</span></div>'
      html = html + '<div><span>' + p['label'] + '</span></div><div><span>' + p['rend'] + '</span></div>'
      print(p['label'] + '=[' + p['rend'] + ']')
    
    html = html + '<div><form action="ok_page" method="get"><button>OK</button></form></div>'
    html = html + '<div><form action="no_page" method="get"><button>NO</button></form></div>'
    html = html + '</div>'
    html = html + '</div>'
    #html = html + '<footer><small>&copy; Copyright 2024, Ecosteer Srl</small></footer>'
    html = html + '</body></html>'
    return html

  def page_ok(self) -> str:
    html: str = '<html><head>'
    html = html + self.style()
    html = html + '</head><body><h1>Configuration Confirmed</h1>'
    html = html + '<div class="content">'
    html = html + '<span>Now you can power off the qubee, change the jumper position and power on again.</span><br><br>'
    html = html + '<span>Ora puoi spegnere il qubee, cambiare la posizione del jumper e riaccenderlo.</span><br>'
    html = html + '</div>'
    #html = html + '<footer><small>&copy; Copyright 2024, Ecosteer Srl</small></footer>'
    html = html + '</body></html>'
    return html


  def http_page(self, page: str) -> str:
    """
      get the input page, generate the header and add the header to the page
    """
    page_len = len(page)
    header: str = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: "
    header = header + str(page_len)
    header = header + "\r\n"
    header = header + "Connection: Close\r\n"
    header = header + "\r\n"

    hp: str = header + page
    return hp

  def configure(self) -> bool:
    # Set up access point parameters
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #s.bind((self.__ip,80))
    s.bind((self.__ip,self.__port))
    s.listen(5)

    while True:
      # accept the incoming connection
      self.__connection, addr = s.accept()
      # as soon as a connection is accepted, check the requested document
      # and forward to the proper page

      #print('Got a connection from %s' % str(addr))
      request = self.__connection.recv(1024)

      # here we need to process the request so the params are used, stored
      # and the loop is closed
      #print('Content = %s' % str(request))
      


      # get the page in the request
      page: str = self.get_request_url(request)
      #print("PAGE: " + page)
      if page == '/':
        #pdb.set_trace()
        html_page = self.page_configuration()
        http_response = self.http_page(html_page)
        #print("Response: " + http_response)
        self.send_response(http_response)
        continue

      # check if the page contains the configuration parameters
      if page.find('/?') >= 0:
        print("CONF PARS: " + page)
        #pdb.set_trace()
        if self.form_data(page[2:]):  # skip the first two chars ('/?')
          html_page = self.page_configuration_check()
          http_response = self.http_page(html_page)
          self.send_response(http_response)
        continue

      if page == '/ok_page?':

        # the user has selected OK, so the configuration can exit
        #pdb.set_trace()
        self.__on_write_failure = False
        if False == self.on_write():
          self.__on_write_failure = True
          http_response = "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n"
          #print("Response: " + http_response)
          self.send_response(http_response)
          continue
        else:
          html_page = self.page_ok()
          http_response = self.http_page(html_page)
          #print("Response: " + http_response)
          self.send_response(http_response)
          break

      if page == '/no_page?':
        # here the browser is redirected to the / page
        http_response = "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n"
        #print("Response: " + http_response)
        self.send_response(http_response)
        continue

      if page == '/stop':
        break

      continue
      

    self.__connection.close()
    return True


#=================================================================================  
#=================================================================================  
#=================================================================================  
#   MAIN SCRIPT FROM HERE
#=================================================================================  
#=================================================================================  
#=================================================================================  

def scan_wifi() -> list:
    wlan = network.WLAN(network.STA_IF)  # Create station interface
    wlan.active(True)  # Activate the station interface

    # Scan for access points
    available_networks = wlan.scan()
    #   see https://docs.micropython.org/en/latest/library/network.WLAN.html

    # Print SSIDs of nearby access points
    """
    print("Available Access Points:")
    for ap in available_networks:
        print("- SSID:", ap[0].decode())  # SSID is stored at index 0
    """
    return available_networks  


def write_configuration(parameters: list) -> bool:
  # this function is used to write to storage the configuration that
  # has been collected by Webbo. The configuration file will contain
  # a json object with a set of properties according to the options
  # passed to the Webbo instance
  #pdb.set_trace()
  try:
    conf_object: dict = {}
    for p in parameters:
      #bv = bytes(p['value'])
      #print(p['id'] + '[' + p['value'] + ']')
      conf_object[p['id']]=p['value']
      #conf_object[p['id']]=bv
    json_object: str = json.dumps(conf_object)
    #print(json_object)

    # write the json conf to the file ap.json
    #f = open('ap.json','w')
    f = open('ap.json','w')
    f.write(json_object)
    f.flush()
    f.close()
  except:
    return False
  return True



aps: list = []
aps_options: list = []


# initialize the aps_options
# the aps_options is a list that holds all the available access points
# from this list the user will choose the AP she wants to connect to
if MODE=='test':
  # for testing and debugging purposes
  # see global MODE at the beginning o dthe program
  aps_options = ['A', 'B', 'C']
else:
  # get all the available access points
  aps: list = scan_wifi()
  # push all the available access points into a list to be used
  # by the dropdown list (Webbo interface)
  for ap in aps:
    ap_ssid = ap[0].decode('utf-8')
    if ap_ssid in aps_options:
      continue
    aps_options.append(ap[0].decode('utf-8'))



# the configuration parameters is a list of objects that
# declare the configuration parameters to be collected from the user
# the configuration parameters are used to dynamically generate
# the necessary web page and to collect the assignments from the 
# resulting (submitted) request pages
configuration_parameters: list = [
  #{"label":"AP SSID", "id":"ssid", "value":"", "options": ['ap-01', 'ap-02', 'ap-03']},   # label - what is shown, id - the id to be used in the form
  {"label":"AP SSID", "id":"ssid", "value":"", "rend": "", "options": aps_options},
  {"label":"Password", "id":"pwd", "value":"", "rend": ""},
  {"label":"Mode", "id":"modeop","value":"", "rend": "", "options":['CONNECTED','STANDALONE']},
  {"label":"Brightness","id":"bright","value":"MEDIUM", "rend":"", "options":['NONE','LOW', 'MEDIUM', 'HIGH']}
]


options: dict = {}
# once the options have been set, the ESP32 has to become an access point
if MODE!='test':

  ap = network.WLAN(network.AP_IF)  # Create access point interface
  ap.active(False)
  ap.active(True)  # Activate the access point
  while ap.active() == False:
    pass

  mac = machine.unique_id()
  client_id = ''.join([f"{b:02X}" for b in mac])

  ssid = f"Qubee_{client_id}"
  ap.config(essid=ssid, authmode=network.AUTH_WPA_WPA2_PSK, password=client_id)  # Configure the access point with SSID and password
  

  # Print the access point information
  print("Access Point started with SSID:", ssid, "and password:", client_id)
  print("Access Point IP Address:", ap.ifconfig()[0])

  options = {
    "configuration_parameters": configuration_parameters,
    "writer":write_configuration,
    "ip": ap.ifconfig()[0],
    "port": 80
  }
else:
   #  MODE=='test'
  options = {
    "configuration_parameters": configuration_parameters,
    "writer":write_configuration,
    "ip": TEST_IP,
    "port":TEST_PORT
  }





# once the AP ha started, time to get the configuration parameters
# and use the Webbo util
# the options to be passed for the Webbo instantiation hold the following
# parameters:
#   configuration_parameters 
#     is a list that contains a set of objects,
#     where each object declares an input to be dynamically created in the configuration page
#     please note that two input types are possible: one without the property "options"
#     and one with the property "options". The inputs with the property options will be implemented
#     as a drop down list and thus the "options" property will have to be assigned to a list
#     in our case the list will contain all the available ssid AP
#
#   writer
#     is a user defined function that has the responsibility to propagate the collected
#     configuration parameters to mass storage so that they can be used after reboot
#     by the process that will send datapoint (using the AP selected during configuration)
#     If the writer is not assigned then at the end of the configuration the user will have
#     the chance to harvest the collected values from the configuration_parameters list
#     as this is used by reference by the webbo. In this case, though, the Webbo will not
#     automatically react to a failure of the writer.
#     If successful the writer MUST return True, in case of failure it MUST return False.
#     The Webbo will react to a failure by showing again the configuration page with a warning.
#
#   ip
#     the IP address the Webbo will bind to. If this parameter is not assined then
#     the Webbo will use the default value of 127.0.0.1


miniWeb = Webbo(options)
miniWeb.configure()






