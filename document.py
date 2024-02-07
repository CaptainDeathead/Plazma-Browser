import tkinter as tk
from tkinter.font import Font
from PIL import ImageTk, Image
import requests
import threading
import convertapi
import os

localappdata = os.getenv('LOCALAPPDATA')
localappdata += "\\Plazma"

class Element:
    def __init__(self, document, scripts, tag, tkElement, globalStyles, htmlId, htmlClass, text, image, styles, src, command):
        print(tag)
        self.document = document
        self.scripts = scripts
        self.tag = tag
        self.id = htmlId # string (1 id)
        self.htmlClass = htmlClass # list of classes (strings; can be multiple classes)
        self.text = text
        self.image = image
        self.styles = styles
        self.innerHTML = text
        self.innerText = text
        self.styles = []
        self.src = src
        self.command = command
        self.children = []
        self.tkElement = tkElement
        print("EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE: " + str(type(tkElement)))
        if tag != 'a':
            try: self.tkElement.config(fg=globalStyles['color'], bg=globalStyles['background'], font=Font(family=globalStyles['font'], size=globalStyles['size']), text=self.text)
            except: pass
            if self.image != None:
                try: self.tkElement.config(image=self.image)
                except: pass
                try:
                    imageThread = threading.Thread(target=self.requestImage)
                    imageThread.start()
                except: pass
        if command != None:
            if 'javascript:' in self.command:
                #self.tkElement.config(command=lambda: exec(self.bigScript + '\n' + self.command.replace('javascript:', '').replace(';', '')))
                self.tkElement.config(command=self.runCmd)
            else:
                self.tkElement.config(command=lambda: exec(command))
        self.tkElement.pack(anchor='w')

    def runCmd(self):
        bigScript = '\n'.join(self.scripts)
        document = self.document
        bigScript.replace('self.', '')
        print(bigScript)
        exec(bigScript + '\n' + self.command.replace('javascript:', '').replace(';', ''))

    def requestImage(self):
        try:
            image = self._img(self.tag)
            if str(image) == "svg": return
            image = Image.open(image)
            image = image.resize((int(image.width/2), int(image.height/2)))
            img = ImageTk.PhotoImage(image)
            self.image = img
            self.tkElement.config(image=self.image)
        except: pass

    def getAndSaveImg(self, link):
        if 'http' not in link and 'https' not in link:
            link = 'http://' + link
        try:
            img_data = requests.get(link, timeout=6).content
            with open(localappdata + f'\\temp\\images\\{link.replace("/", "").replace(":", "")}', 'wb') as handler:
                handler.write(img_data)
                handler.close()
            try:
                if link.replace("/", "").replace(":", "")[-3:] == 'svg':
                    convertapi.api_secret = 'Gi5wMEzioInYhY1U'
                    convertapi.convert('png', {
                        'File': localappdata + f'\\temp\\images\\{link.replace("/", "").replace(":", "")}'
                    }, from_format = 'svg').save_files(localappdata + '\\temp\\images')
                    link = list(link.replace("/", "").replace(":", ""))
                    link[-3:] = ['p', 'n', 'g']
                    link = ''.join(link)
                    print("NEW LINK: " + link)
                    image = Image.open(localappdata + f'\\temp\\images\\{link}')
                    image = image.resize((int(image.width/2), int(image.height/2)))
                    img = ImageTk.PhotoImage(image)
                    self.image = img
                    self.tkElement.config(image=self.image)
                    return "svg"
            except Exception as e: print("SVG IMAGE LOADING ERROR: " + str(e))
            return "Ok"
        except:
            return "None"

    def _img(self, tag):
        link = self.src
        if link == "None": return None
        else:
            status = self.getAndSaveImg(link)
            #print(status)
            if status == "None": return None
            elif status == "svg": return "svg"
            else: return localappdata + f'\\temp\\images\\{link.replace("/", "").replace(":", "")}'

    def setAttribute(self, attr, value):
        try:
            exec('self.' + attr + '="' + value + '"')
            exec(f"self.tkElement.config({attr}='{value}')")
        except Exception as e: print("SET ATTRIBUTE ERR: " + str(e))

    def draw(self, globalStyles):
        try: self.tkElement.config(text=self.text)
        except: pass
        try:
            if self.image != None: self.tkElement.config(image=self.image)
        except: pass
        try: self.tkElement.config(font=Font(family=globalStyles[self.tag]['font'], size=globalStyles[self.tag]['size']))
        except: pass
        try: self.tkElement.config(background=globalStyles[self.tag]['background'])
        except: pass
        try: self.tkElement.config(fg=globalStyles[self.tag]['color'])
        except: pass
        #self.tkElement.pack(anchor='w')

    def appendChild(self, element):
        element.styles.extend(self.styles)
        self.children.append(element)

class Document:
    def __init__(self):
        self.elements = []
        self.styles = {}
        self.scripts = []

    def innerHTML(self, elementId):
        return self.elements[elementId].innerHTML
    
    def checkElements(self, elements):
        for i in range(len(elements)):
            if elements[i]["innerHTML"] != self.elements[i].innerHTML:
                self.elements[i].innerHTML = elements[i]["innerHTML"]
                self.elements[i].tkElement.config(text=self.elements[i].innerHTML)

    def getElementById(self, elementId):
        for element in self.elements:
            if element.id == elementId:
                return self.elements.index(element)

    def getElementsByClassName(self, name):
        elementsWithClass = []
        for element in self.elements:
            if element.htmlClass == name: elementsWithClass.append(element)
        return elementsWithClass
    
    def createElement(self, tag, tkElement, htmlId="html", htmlClass="html", text="", image='', styles=[], src="", command=None):
        self.elements.append(Element(self, self.scripts, tag, tkElement, self.styles[tag], htmlId, htmlClass, text, image, styles, src, command))
        return self.elements[-1]
    
    #def draw(self):
    #    for element in self.elements:
    #        if element.tag == 'a': continue
    #        element.draw(self.styles)

class Window:
    def __init__(self):
        ...