#!/usr/bin/env python3

import PyPDF2
import re
import os
import subprocess


class DocumentSection:
    def __init__(self, title, page_from, page_to, path):
        self.title = title
        self.page_from = page_from
        self.page_to = page_to
        self.path = path


class SectionManager:
    def __init__(self, rm_path):
        self.rm_path = rm_path

    _section_list = list()

    def analyze(self, force=False):
        regex_peripheral = r'.+\(([A-Za-z0-9/]+)\).*'
        section_list = list()
        page_number_needed = False
        try:
            document = PyPDF2.PdfFileReader(open(self.rm_path, 'rb'))

            for section in document.getOutlines():
                if '/Title' in section:
                    match = re.match(regex_peripheral, section['/Title'])
                    if page_number_needed:
                        section_list[-1].page_to = document.getDestinationPageNumber(section)
                        page_number_needed = False
                    if match:
                        title = match.group(1).replace('/', '_')
                        section_list.append(DocumentSection(match.group(1),
                                                            document.getDestinationPageNumber(section),
                                                            None,
                                                            self.rm_path + '.' + title + '.pdf'))
                        page_number_needed = True
            self._section_list = section_list
            return self._section_list
        except:
            return None

    def extract2(self):
        document = PyPDF2.PdfFileReader(open(self.rm_path, 'rb'))
        for s in self._section_list:
            output = PyPDF2.PdfFileWriter()
            for pn in range(s.page_from, s.page_to):
                output.addPage(document.getPage(pn))
            output.write(open(s.path, "wb"))

    def extract(self):
        for s in self._section_list:
            if not os.path.isfile(s.path):
                print('Extraction section {}'.format(s.path))
                # qpdf command syntax: `qpdf --empty --pages RM0367.pdf 70-120 -- test3.pdf`
                # TODO: Split PDF in a way, that preserves the link functionality
                subprocess.run(['qpdf',
                                '--empty',
                                '--pages',
                                self.rm_path,
                                '{}-{}'.format(s.page_from + 1, s.page_to),
                                '--',
                                s.path])
            else:
                print('Section {} already exists.'.format(s.path))

    def get_section_list(self):
        return self._section_list
