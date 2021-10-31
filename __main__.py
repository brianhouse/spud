#!/usr/bin/env python3

import os, sys, yaml, markdown, shutil, jinja2, re, subprocess, time, datetime, json
from PIL import Image
from pprint import pprint


try:
    subprocess.check_call("exiftool -all= images/*", shell=True)      # security / helps opengraph
except Exception as e:
    print(e)
try:
    subprocess.check_call("rm images/*_original &> /dev/null", shell=True)
except Exception as e:
    pass
filenames = [filename for filename in os.listdir("images") if os.path.splitext(filename)[-1] == ".jpg"]

def get_images(name):
    images = [filename for filename in filenames if filename[:len(name)] == name and "@2x" not in filename]
    images.sort()
    for i, image in enumerate(images):
        hires = [filename for filename in filenames if os.path.splitext(filename)[0] == os.path.splitext(image)[0] + "@2x"]
        images[i] = image, hires[0] if len(hires) else None
    return images


def build():

    # load content
    with open("structure.yaml") as f:
        structure = yaml.safe_load(f)
    structure = {'sections': structure['www'], 'info': load_yaml(os.path.join("pages", "www.yaml"))}
    sections = structure['sections']
    for section_name, section in sections.items():
        section = {'content': load_yaml(os.path.join("pages", f"{section_name}.yaml")), 'children': section, 'images': get_images(section_name)}
        if section['children'] is not None:
            for c, child_name in enumerate(section['children']):
                child = {'page': child_name, 'content': load_yaml(os.path.join("pages", f"{section_name}", f"{child_name}.yaml")), 'images': get_images(child_name)}
                section['children'][c] = child
        sections[section_name] = section

    # render files
    directory = "www"
    if not os.path.isdir(directory):
        os.mkdir(directory)
    template = os.path.join("spud", "templates", "www.html")
    if os.path.isfile(template):
        html = render(template, {}, structure=structure, info=structure['info'])
        html_path = os.path.join("www", "index.html")
        with open(html_path, 'w') as f:
            f.write(html)

    for section_name, section in sections.items():

        # top-level section
        directory = os.path.join("www", section_name)
        if not os.path.isdir(directory):
            os.mkdir(directory)
        if section['content'] is not None:
            template = os.path.join("spud", "templates", f"{section_name}.html")
            if os.path.isfile(template):
                html = render(template, section['content'], structure=structure, info=structure['info'])
                html_path = os.path.join(directory, "index.html")
                with open(html_path, 'w') as f:
                    f.write(html)
        for image in section['images']:
            for res in image:
                if res is not None:
                    source_path = os.path.join("images", res)
                    destination_path = os.path.join(directory, res)
                    shutil.copy(source_path, destination_path)

        # subpages
        if section['children'] is not None:
            for child in section['children']:
                child_name = child['page']
                print(child_name)
                directory = os.path.join("www", section_name, child_name)
                if not os.path.isdir(directory):
                    os.mkdir(directory)
                template = os.path.join("spud", "templates", "%s.html" % section_name.strip('s') if section_name[-1] == "s" else child_name + ".html")
                print("\t", template)
                if os.path.isfile(template):
                    html = render(template, child['content'], images=child['images'], structure=structure, info=structure['info'], page=child_name)
                    html_path = os.path.join(directory, "index.html")
                    with open(html_path, 'w') as f:
                        f.write(html)
                for image in child['images']:
                    for res in image:
                        if res is not None:
                            source_path = os.path.join("images", res)
                            destination_path = os.path.join(directory, res)
                            shutil.copy(source_path, destination_path)


# how does that work in detecting if the file has changed?
#             if os.path.isfile(template) and os.path.isfile(content) and (not os.path.isfile(html_path) or (os.path.getmtime(template) > os.path.getmtime(html_path)) or (os.path.getmtime(content) > os.path.getmtime(html_path))):



def load_yaml(path):
    data = None
    if '.' in os.path.splitext(path)[0]:
        path = path.split('.')[0] + ".yaml"
    if os.path.isfile(path):
        with open(path) as f:
            data = yaml.safe_load(f)
            md(data)
    return data

def render(template_name, data=None, **kwargs):
    template_values = kwargs
    if data is not None:
        template_values.update(data)
    renderer = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
    renderer.filters.update({'slugify': slugify, 'unslugify': unslugify, 'strip_html': strip_html, 'strip_quotes': strip_quotes, 'strslice': strslice, 'is_list': is_list})
    output = renderer.get_template(template_name).render(template_values)
    return output

def md(data):
    if type(data) is dict:
        if 'text' in data:
            data['text'] = markdown.markdown(data['text'].strip())
        else:
            for key in data:
                md(data[key])
    elif type(data) is list:
        for item in data:
            md(item)

def slugify(value, punctuation=False):
    if not punctuation:
        value = re.sub(r'[^\w\s\.-]', '', value)
    value = value.strip().lower()
    return re.sub(r'[\s]+', '_', value)

def unslugify(s):
    s = s.replace('_', ' ')
    s = re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), s.title()).split()
    s = ' '.join([(s.lower() if s.lower() in ['for', 'in', 'to', 'a', 'of', 'the', 'or'] and i != 0 else s) for (i, s) in enumerate(s)])
    return s

def strip_html(s, keep_links=False):
    if keep_links:
        s = re.sub(r'</[^aA].*?>', '', s)
        s = re.sub(r'<[^/aA].*?>', '', s)
        return s
    else:
        return re.sub(r'<.*?>', '', s)

def strip_quotes(s):
    return s.replace('"', '')

def strslice(s, length):
    if not type(s) == str:
        s = str(s)
    return s[:length]

def is_list(value):
    return isinstance(value, list)

def copy_static():
    for filename in os.listdir(os.path.join("spud", "static")):
        if filename[0] != "." and not os.path.isdir(os.path.join("spud", "static", filename)):
            shutil.copy(os.path.join("spud", "static", filename), "www")
    for filename in os.listdir(os.path.join("spud", "static", "js")):
        if filename[0] != "." and not os.path.isdir(os.path.join("static", filename)):
            shutil.copy(os.path.join("spud", "static", "js", filename), "www")
    for filename in os.listdir("icons"):
        if filename[0] != "." and not os.path.isdir(os.path.join("static", filename)):
            shutil.copy(os.path.join("icons", filename), "www")
    shutil.copy(os.path.join("spud", "style.css"), "www")

if __name__ == "__main__":
    if not len(sys.argv) > 1:
        print("[generate|rebuild|test]")
        exit()
    if sys.argv[1] == "test":
        try:
            subprocess.check_call(f"python3 -m http.server --directory www/ 8000", shell=True)
        except:
            pass
        exit()
    elif sys.argv[1] == "rebuild":
        rebuild = True
        print("Rebuilding all HTML")
    elif sys.argv[1] == "generate":
        print("Generating needed HTML")
    else:
        print("[generate|rebuild|test]")
        exit()
    build()
    copy_static()
