#!/usr/bin/python
def gettemp(id):
  try:
    mytemp = ''
    filename = 'w1_slave'
    f = open('/sys/bus/w1/devices/' + id + '/' + filename, 'r')
    line = f.readline() # read 1st line
    crc = line.rsplit(' ',1)
    crc = crc[1].replace('\n', '')
    if crc=='YES':
      line = f.readline() # read 2nd line
      mytemp = line.rsplit('t=',1)
    else:
      mytemp = 99999
    f.close()
 
    return (float)(mytemp[1])/1000
 
  except:
    return 99999
 
if __name__ == '__main__':
 
  # Script has been called directly
  id = '28-02148151b0ff' #beer
  print("Temp : " + '{:.3f}'.format(gettemp(id)))

  id = '28-0417004ebfff' #chamber
  print("Temp : " + '{:.3f}'.format(gettemp(id)))

