import os

def checkNumber(value, field_name):
    try:
        float(value)
    except ValueError:
        raise Exception(str(field_name) + " is not a number")

    return value

def checkPositiveNumber(value, field_name):
    value = checkNumber(value, field_name)
    if (value < 0): raise Exception(field_name + " should be >= 0")

    return value

def checkStrictlyPositiveNumber(value, field_name):
    value = checkNumber(value, field_name)
    if (value <= 0): raise Exception(field_name + " should be > 0")

    return value

def checkAngle(value, field_name):
    value = checkNumber(value, field_name)
    if value < -360 or value > 360: raise Exception(field_name + " should be >= -360 and <= 360 deg")

    return value

def checkPositiveAngle(value, field_name):
    value = checkNumber(value, field_name)
    if value < 0 or value > 360: raise Exception(field_name + " should be >= 0 and <= 360 deg")

    return value

def checkStrictlyPositiveAngle(value, field_name):
    value = checkNumber(value, field_name)
    if value <= 0 or value >= 360: raise Exception(field_name + " should be > 0 and < 360 deg")

    return value

def checkEmptyString(string, field_name):
    if string is None: raise Exception(field_name + " should not be an empty string")
    if string.strip() == "": raise Exception(field_name + " should not be an empty string")

    return string

def checkGreaterThan(number1, number2, field_name1, field_name_2):
    if number1 <= number2: raise Exception(field_name1 + " should be greater than " + field_name_2)

def checkGreaterOrEqualThan(number1, number2, field_name1, field_name_2):
    if number1 < number2: raise Exception(field_name1 + " should be greater or equal than " + field_name_2)

def checkLessThan(number1, number2, field_name1, field_name_2):
    if number1 >= number2: raise Exception(field_name1 + " should be less than " + field_name_2)

def checkLessOrEqualThan(number1, number2, field_name1, field_name_2):
    if number1 > number2: raise Exception(field_name1 + " should be less or equal than " + field_name_2)

def checkEqualTo(number1, number2, field_name1, field_name_2):
    if number1 != number2: raise Exception(field_name1 + " should be equal to " + field_name_2)

def checkFileName(fileName):
    if isinstance(fileName, bytes): fileName = fileName.decode('utf-8')

    if fileName is None: raise Exception("File name is Empty")
    if fileName.strip() == "": raise Exception("File name is Empty")

    if os.path.isabs(fileName):
        filePath = fileName
    else:
        if fileName.startswith(os.path.sep):
            filePath =  os.getcwd() + fileName
        else:
            filePath = os.getcwd() + os.path.sep + fileName

    return filePath

def checkDir(fileName):
    if isinstance(fileName, bytes): fileName = fileName.decode('utf-8')

    filePath = checkFileName(fileName)

    container_dir = os.path.dirname(filePath)

    if not os.path.exists(container_dir):
        raise Exception("Directory " + container_dir + " not existing")

    return filePath

def checkFile(fileName):
    if isinstance(fileName, bytes): fileName = fileName.decode('utf-8')

    filePath = checkDir(fileName)

    if not os.path.exists(filePath):
        raise Exception("File " + fileName + " not existing")

    return filePath


def checkUrl(myfileurl):
    from urllib.request import urlopen
    try:
        u = urlopen(myfileurl)
    except:
        try:
            return checkFile(myfileurl)
        except:
            raise Exception("URL or File not accessible: "+myfileurl)

    return myfileurl
