#!/usr/bin/env python3

from stdata import document

x = document.DocumentManager()
# x.update(update_pdfs=True)
# x.analyze_rms()
# for d in x.get_rm_list():
#     print(d.parts)
#     print(d.title, '\t|| ', d.description)
#     for s in d.sections.get_section_list():
#         print('\t\t||  > ' + s.title)
#     print('===============')

x.find_similarities('ADC')
