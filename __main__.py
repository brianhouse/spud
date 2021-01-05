#!/usr/bin/env python3

import os, sys, yaml, markdown, shutil, jinja2, re, subprocess, time, datetime, json
from PIL import Image
from pprint import pprint

rebuild = False
images = None

def process_images():
    try:
        subprocess.check_call("exiftool -all= images/*", shell=True)      # security / helps opengraph
    except Exception as e:
        print(e)
        exit()
    try:
        subprocess.check_call("rm images/*_original &> /dev/null", shell=True)
    except Exception:
        pass
    images = {}
    filenames = list(os.listdir("images"))
    filenames.sort()
    for filename in filenames:
        if ".jpg" not in filename:
            continue
        slug = filename.split(".")[0].replace("@2x", "")
        tag = slug.split("_")[-1]
        try:
            int(tag)
            slug = slug[:-(len(tag) + 1)]
        except ValueError:
            pass
        if slug not in images:
            images[slug] = []
        if "@2x" in filename:
            images[slug][-1][1] = filename
        else:
            images[slug].append([filename, None])
    # print(json.dumps(images, indent=4))
    return images

def build(structure, root):
    if structure is None:
        return False, None
    else:
        update_parent = False
        pages = structure.keys() if type(structure) is dict else structure
        sibling_data = {}
        for page in pages:
            path = os.path.join(root, slugify(page)) # . has to survive
            parts = root.split('/')[2:]
            parts.append(slugify(page.split('.')[0]))
            content = f"pages/{'/'.join(parts)}.yaml"
            if type(structure) is dict:
                template = "spud/templates/%s.html" % slugify(page)
            else:
                template = "spud/templates/%s.html" % root.split("/")[-1].split("_")[-1][:-1]
            html_path = os.path.join(path, "index.html")
            data = {'page': page}
            if os.path.isfile(content):
                with open(content) as f:
                    data.update(yaml.safe_load(f))
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
                md(data)
            build_page = False if ('build' in data and data['build'] is False) else True
            if not build_page:
                path = '/'.join(path.split('/')[:-1])
            else:
                if not os.path.isdir(path):
                    os.mkdir(path)
            data['path'] = path
            update = False
            page_images = []
            if slugify(page) in images:
                for (image, hires) in images[slugify(page)]:
                    image_source_path = os.path.join("images", image)
                    image_destination_path = os.path.join(path, image_source_path.split("/")[-1])
                    if not os.path.isfile(image_destination_path) or os.path.getmtime(image_source_path) > os.path.getmtime(image_destination_path):
                        shutil.copy(image_source_path, image_destination_path)
                        print("\t--> copying %s..." % image)
                        update = True
                    if hires is not None:
                        hires_source_path = os.path.join("images", hires)
                        hires_destination_path = os.path.join(path, hires_source_path.split("/")[-1])
                        if not os.path.isfile(hires_destination_path) or os.path.getmtime(hires_source_path) > os.path.getmtime(hires_destination_path):
                            shutil.copy(hires_source_path, hires_destination_path)
                            print("\t--> copying %s hires..." % hires)
                            update = True
                    width, height = Image.open(image_source_path).size
                    page_images.append((image, width, height, hires))
            data.update({'images': page_images})
            if type(structure) is dict:
                update, child_data = build(structure[page], path)
                if child_data:
                    data['child_data'] = child_data
            if os.path.isfile(template) and os.path.isfile(content) and (not os.path.isfile(html_path) or (os.path.getmtime(template) > os.path.getmtime(html_path)) or (os.path.getmtime(content) > os.path.getmtime(html_path))):
                # print("\t--> updating content: %s\twith template: %s" % (content, template))
                update = True
            elif os.path.isfile(template) and (not os.path.isfile(html_path) or (os.path.getmtime(template) > os.path.getmtime(html_path))):
                # print("\t--> updating template: %s" % template)
                update = True
            if rebuild:
                update = True
            print(f"PAGE: {root.split('./')[-1]}/{page}")
            if update:
                if build_page:
                    print(f"\t--> updating")
                    html = render(template, data, image_structure=images, structure=(structure[page] if type(structure) is dict else None))
                    with open(html_path, 'w') as f:
                        f.write(html)
                update_parent = True
            sibling_data[page] = data
        return update_parent, sibling_data

def render(template_name, data=None, **kwargs):
    template_values = kwargs
    if type(data) == dict:
        template_values.update(data)
    renderer = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
    renderer.filters.update({'slugify': slugify, 'unslugify': unslugify, 'strip_html': strip_html, 'strip_quotes': strip_quotes, 'strslice': strslice, 'is_list': is_list})
    output = renderer.get_template(template_name).render(template_values)
    return output

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

def copy_static(root):
    for filename in os.listdir(os.path.join("spud", "static")):
        if filename[0] != "." and not os.path.isdir(os.path.join("spud", "static", filename)):
            shutil.copy(os.path.join("spud", "static", filename), f"{root}/")
    for filename in os.listdir(os.path.join("spud", "static", "js")):
        if filename[0] != "." and not os.path.isdir(os.path.join("static", filename)):
            shutil.copy(os.path.join("spud", "static", "js", filename), f"{root}/")
    for filename in os.listdir("icons"):
        if filename[0] != "." and not os.path.isdir(os.path.join("static", filename)):
            shutil.copy(os.path.join("icons", filename), f"{root}/")

if __name__ == "__main__":
    if not len(sys.argv) > 1:
        print("[generate|rebuild|test]")
        exit()
    with open("structure.yaml") as f:
        structure = yaml.safe_load(f)
    root = list(structure.keys())[0]
    if sys.argv[1] == "test":
        try:
            subprocess.check_call(f"python3 -m http.server --directory {root}/ 8000", shell=True)
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
    images = process_images()
    build(structure, ".")
    copy_static(root)
