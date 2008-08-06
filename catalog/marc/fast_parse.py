# fast parse for merge
# TODO: title and author
# TODO: handle MARC8 charset

import re

re_question = re.compile('^\?+$')
re_lccn = re.compile('(...\d+).*')
re_letters = re.compile('[A-Za-z]')
re_int = re.compile ('\d{2,}')
re_isbn = re.compile('([^ ()]+[\dX])(?: \((?:v\. (\d+)(?: : )?)?(.*)\))?')
re_oclc = re.compile ('^\(OCoLC\).*?0*(\d+)')

re_normalize = re.compile('[^\w ]')
re_whitespace = re.compile('\s+')

def normalize(s):
    s = re_normalize.sub('', s.strip())
    s = re_whitespace.sub(' ', s)
    return s.lower()

# no monograph should be longer than 50,000 pages
max_number_of_pages = 50000

def read_author_person(line):
    name = []
    name_and_date = []
    for k, v in get_subfields(line, ['a', 'b', 'c', 'd']):
        if k != 'd':
            v = v.strip(' /,;:')
            name.append(v)
        name_and_date.append(v)
    if not name:
        return []

    return [{ 'db_name': ' '.join(name_and_date), 'name': ' '.join(name), }]

def read_full_title(line):
    return ' '.join(v.strip(' /,;:') for k, v in get_subfields(line, ['a', 'b']))

def read_short_title(line):
    prefix_len = line[1]
    title_and_subtitle = []
    title = []
    for k, v in get_subfields(line, ['a', 'b']):
        v = v.strip(' /,;:')
        title_and_subtitle.append(v)
        if k == 'a':
            title.append(v)
    
    titles = [' '.join(title).strip()]
    if title != title_and_subtitle:
        titles.append(' '.join(title_and_subtitle).strip())
    if prefix_len and prefix_len != '0':
        try:
            prefix_len = int(prefix_len)
            titles += [t[prefix_len:] for t in titles]
        except ValueError:
            pass
    return [str(normalize(i)[:25]) for i in titles]

def get_subfields(line, want):
    want = set(want)
    #assert line[2] == '\x1f'
    for i in line[3:-1].split('\x1f'):
        if i and i[0] in want:
            yield i[0], i[1:]

def get_tag_lines(data, want):
    want = set(want)
    dir_end = data.find(chr(30))
    directory = data[24:dir_end]
    if len(directory) % 12 != 0:
        # directory is the wrong size
        # sometimes the leader includes some utf-8 by mistake
        directory = data[:dir_end].decode('utf-8')[24:]
        assert len(directory) % 12 == 0

    fields = []

    for i in range(len(directory) / 12):
        line = directory[i*12:(i+1)*12]
        tag = line[:3]
        if tag not in want:
            continue
        length = int(line[3:7])
        offset = int(line[7:12])
        tag_line = data[dir_end+offset + 1:dir_end+1+length+offset]
        assert ord(tag_line[-1]) == 30
        fields.append((tag, tag_line))
    return fields

def read_lccn(line):
    found = []
    for k, v in get_subfields(line, ['a']):
        lccn = v.strip()
        if re_question.match(lccn):
            continue
        m = re_lccn.search(lccn)
        if not m:
            continue
        lccn = re_letters.sub('', m.group(1)).strip()
        if lccn:
            found.append(lccn)
    return found

def read_isbn(line):
    found = []
    if line.find('\x1f') != -1:
        for k, v in get_subfields(line, ['a', 'z']):
            m = re_isbn.match(v)
            if m:
                found.append(m.group(1))
    else:
        m = re_isbn.match(line[3:-1])
        if m:
            return [m.group(1)]
    return [i.replace('-', '') for i in found]

def read_oclc(line):
    found = []
    for k, v in get_subfields(line, ['a']):
        m = re_oclc.match(v)
        if m:
            found.append(m.group(1))
    return found

def read_publisher(line):
    return [v.strip(' /,;:') for k, v in get_subfields(line, ['b'])]

def read_author_org(line):
    name = " ".join(v.strip(' /,;:') for k, v in get_subfields(line, ['a', 'b']))
    return [{ 'name': name, 'db_name': name, }]

def read_author_event(line):
    name = " ".join(v.strip(' /,;:') for k, v in get_subfields(line, ['a', 'b', 'd', 'n']))
    return [{ 'name': name, 'db_name': name, }]

def read_edition(data, get_short_title = True):
    edition = {}
    want = ['008', '010', '020', '035', '100', '110', '111', '245', '260', '300']
    fields = get_tag_lines(data, want)
    read_tag = [
        ('010', read_lccn, 'lccn'),
        ('020', read_isbn, 'isbn'),
        ('035', read_oclc, 'oclc'),
        ('100', read_author_person, 'authors'),
        ('110', read_author_org, 'authors'),
        ('111', read_author_event, 'authors'),
        ('260', read_publisher, 'publisher'),
    ]

    if get_short_title:
        read_tag.append(('245', read_short_title, 'short_title'))

    for tag, line in fields:
        if tag == '008':
            edition['publish_date'] = line[7:11]
            continue
        for t, proc, key in read_tag:
            if t != tag:
                continue
            found = proc(line)
            if found:
                edition.setdefault(key, []).extend(found)
            break
        if tag == '245':
            edition['full_title'] = read_full_title(line)
        if tag == '300':
            for k, v in get_subfields(line, ['a']):
                num = [ int(i) for i in re_int.findall(v) ]
                num = [i for i in num if i < max_number_of_pages]
                if not num:
                    continue
                max_page_num = max(num)
                if 'number_of_pages' not in edition \
                        or max_page_num > edition['number_of_pages']:
                    edition['number_of_pages'] = max_page_num
    return edition