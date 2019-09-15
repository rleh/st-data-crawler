#!/usr/bin/env python3

import json
import urllib.request
import shutil
import pickle
import os
import multiprocessing
import pdftotext
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AffinityPropagation
import numpy as np

from .section import SectionManager


class Document:
    def __init__(self, type, title, description, url, parts, path, sections):
        self.type = type
        self.title = title
        self.description = description
        self.url = url
        self.parts = parts
        self.path = path
        self.sections = sections


class DocumentManager:
    rm_url = 'https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus.cxst-rs-grid.html/CL1734.technical_literature.reference_manual.json'
    ds_urls = [
        'https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-high-performance-mcus.cxst-rs-grid.html/SC2154.technical_literature.datasheet.json',
        'https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-mainstream-mcus.cxst-rs-grid.html/SC2155.technical_literature.datasheet.json',
        'https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-ultra-low-power-mcus.cxst-rs-grid.html/SC2157.technical_literature.datasheet.json',
        'https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-wireless-mcus.cxst-rs-grid.html/SC2156.technical_literature.datasheet.json',
    ]
    hdr = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'}

    _rm_list = list()
    _ds_list = list()

    _data_dir = '.stdata/data/'
    _data_document_dir = '.stdata/data/documents/'
    _rm_list_filename = '.stdata/data/rm_list.pkl'
    _ds_list_filename = '.stdata/data/ds_list.pkl'

    def __init__(self):
        if os.path.isfile(self._rm_list_filename) and os.path.isfile(self._ds_list_filename):
            print('Info: Restored data from {}'.format(self._data_dir))
            self._rm_list = pickle.load(open(self._rm_list_filename, 'rb'))
            self._ds_list = pickle.load(open(self._ds_list_filename, 'rb'))

    def store_data(self):
        os.makedirs(self._data_dir, exist_ok=True)
        pickle.dump(self._rm_list, open(self._rm_list_filename, 'wb'))
        pickle.dump(self._ds_list, open(self._ds_list_filename, 'wb'))

    def update_rm_list(self):
        rm_list = list()
        with urllib.request.urlopen(urllib.request.Request(self.rm_url, headers=self.hdr)) as url:
            data = json.loads(url.read().decode())
            rows = data['rows']
            for row in rows:
                rm_list.append(Document(
                    'RM',
                    row['title'],
                    row['localizedDescriptions']['en'],
                    'https://www.st.com' + row['localizedLinks']['en'],
                    [pn['text'] for pn in row['partNumbers']],
                    self._data_document_dir + row['title'] + '.pdf',
                    None,
                )
                )
        self._rm_list = rm_list

    def update_ds_list(self):
        ds_list = list()
        for url in self.ds_urls:
            with urllib.request.urlopen(urllib.request.Request(url, headers=self.hdr)) as url:
                data = json.loads(url.read().decode())
                rows = data['rows']
                for row in rows:
                    ds_list.append(Document(
                        'DS',
                        row['title'],
                        row['localizedDescriptions']['en'],
                        'https://www.st.com' + row['localizedLinks']['en'],
                        [pn['text'] for pn in row['partNumbers']],
                        None,
                        None,
                    )
                    )
        self._ds_list = ds_list

    def download_pdf(self, d):
        os.makedirs(self._data_document_dir, exist_ok=True)
        if not os.path.isfile(d.path):
            print('Downloading file {} ...'.format(d.url))
            with urllib.request.urlopen(urllib.request.Request(d.url, headers=self.hdr)) as response,\
                    open(d.path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        else:
            print('Document {} already exists.'.format(d.path))

    def update(self, update_pdfs=True):
        # self.update_ds_list()
        self.update_rm_list()
        if update_pdfs:
            with multiprocessing.Pool(10) as pool:
                pool.map(self.download_pdf, self._ds_list + self._rm_list)
        self.store_data()

    def _process_rm(self, rm):
        if not rm.sections:
            sections = SectionManager(rm.path)
            sections.analyze()
            sections.extract()
            rm.sections = sections
            return rm

    def analyze_rms(self):
        with multiprocessing.Pool(4) as pool:
            rm_list = pool.map(self._process_rm, self._rm_list)
        self._rm_list = rm_list
        self.store_data()

    def get_ds_list(self):
        return self._ds_list

    def get_rm_list(self):
        return self._rm_list

    def find_similarities(self, section_title):
        section_list = list()
        for rm in self._rm_list: # [0:10]:  # TEST mode
            found = False
            for s in rm.sections.get_section_list():
                if s.title == section_title:  # TODO: Regex?
                    if found:
                        print('ERROR: Section {} found multiple times in document {}'.format(section_title, rm.path))
                    section_list.append(s)
                    found = True
            if not found:
                section_list.append(None)
                print('ERROR: Section {} not found in document {}'.format(section_title, rm.path))
        text_list = list()
        text_list_len = list()
        for s in section_list:
            if s is None:
                text_list.append('')
                text_list_len.append(0)
            else:
                pdf = pdftotext.PDF(open(s.path, "rb"))
                text_list.append('\n\n'.join(pdf))
                text_list_len.append(len(pdf))
        # https://stackoverflow.com/questions/8897593/how-to-compute-the-similarity-between-two-text-documents#24129170
        vect = TfidfVectorizer(min_df=1, stop_words="english")
        tfidf = vect.fit_transform(text_list)
        pairwise_similarity = tfidf * tfidf.T

        clustering = AffinityPropagation().fit_predict(pairwise_similarity)
        for group in range(0, max(clustering) + 1):
            print('Similar {} peripherals: '.format(section_title))
            for index in range(0, len(clustering)):
                if clustering[index] == group:
                    print('\t[{:2d}] {}, {:3d}S: {}'.format(index, self._rm_list[index].title, text_list_len[index],self._rm_list[index].description))
        print('\n')
