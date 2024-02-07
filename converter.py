#js2py.translate_file('testjs.js', 'example.py')

###pycode = open('testjs.js', 'r').read()
import os

localappdata = os.getenv('LOCALAPPDATA')
localappdata += "\\Plazma"

print("E")

def callRemoveSpaces(script):
    script = '\n'.join(removeSpaces(script))
    spaces = ""
    for i, char in enumerate(list(script)):
        if char == ' ':
            spaces += " "
        else: break
    script = script.splitlines()
    for i in range(len(script)):
        script[i] = script[i][len(spaces):]
    script = '\n'.join(script)
    return script

def removeSpaces(script):
    script = script.splitlines()
    for i in range(len(script)):
        if len(script[i]) == 0: script.pop(i)
        for char in script[i]:
            if len(script[i]) == 0:
                script = script.pop(0)
                break
            if char != ' ' and len(script) > 0: return script

def main():
    pycode = open(localappdata + '\\temp\\script.js', 'r').read()

    replacers = {
        ';': '',
        '}': '',
        '{': ':',
        'function': 'def',
        'console.log': 'print',
        'var ': '',
        'let ': '',
        '&&': 'and',
        '||': 'or',
        '===': '==',
        '!==': '!=',
        '<==': '<=',
        '>==': '>==',
        '//': '#',
        '/*': '"""',
        '*/': '"""',
        'new ': '',
        'def()': 'lambda',
        'this': 'self',
        '++': '+=1',
        '--': '-=1',
        'undefined': 'None',
        'true': 'True',
        'false': 'False',
        'indexOf': 'index',
        'document': 'self.document'
    }

    attrReplacers = {
        'innerHTML': 'text',
        'innerText': 'text'
    }

    forSpecialReplacers = [';', '++', '--']

    pycode = pycode.split('\n')
    for i, line in enumerate(pycode):
        try:
            for key in attrReplacers.keys():
                if key in line:
                    index = pycode[i].find(key)
                    if index != -1:
                        endChar = None
                        for arIndex, ar in enumerate(list(pycode[i])[index:]):
                            if ar == '"' or ar == "'":
                                endChar = ar
                                break
                        if endChar != None:
                            print("ENDCHAR: " + endChar)
                            pycode[i] = ''.join(list(pycode[i])[:index]) + 'setAttribute("' + attrReplacers[key] + '", ' + ''.join(list(pycode[i])[index+arIndex:]) + ')'
                        else:
                            value = pycode[i].replace(' ', '').split('=')[1]
                            pycode[i] = ''.join(list(pycode[i])[:index]) + 'setAttribute("' + attrReplacers[key] + '", ' + value + ')'
            if 'for (' in line or 'for(' in line:
                pycode[i] = pycode[i].replace('for (', 'for ').replace('for(', 'for ')
                if pycode[i].count(';') == 2:
                    variable = pycode[i].replace(' ', '').split('var')[1][0]
                    if '<' in pycode[i]:
                        total = pycode[i].replace(' ', '').replace('=', '').split('<')[1].split(';')[0]
                    else:
                        print("EEE")
                        continue
                    beforeFor = ""
                    for j in range(pycode[i].index('for')):
                        beforeFor += pycode[i][j]
                    pycode[i] = f'{beforeFor}for {variable} in range({total}):'
                else: print(i, pycode[i].count(';'))
            else:
                for key in replacers.keys():
                    pycode[i] = pycode[i].replace(key, replacers[key])
                    #if key in line: print(pycode[i], key)
        except Exception as e: print(f"An error occured in the replacement section:\n\n-> {e}")

    pycode = '\n'.join(pycode)

    #pycode = '## Added code\nfrom document import Document, Window\n\ndocument = Document()\nwindow = Window()\n\n# Converted Code\n' + pycode

    open(localappdata + '\\temp\\script.py', 'w').write(pycode)