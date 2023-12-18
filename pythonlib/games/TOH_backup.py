def extract_tss_XML_backup(self, tss, file_name, xml_path):
    root = etree.Element('SceneText')

    tss.seek(0)
    tss.read(12)
    strings_offset = struct.unpack('<I', tss.read(4))[0]
    tss.read(4)
    pointer_block_size = struct.unpack('<I', tss.read(4))[0]
    block_size = struct.unpack('<I', tss.read(4))[0]

    # Create all the Nodes for Struct
    speaker_node = etree.SubElement(root, 'Speakers')
    etree.SubElement(speaker_node, 'Section').text = "Speaker"
    strings_node = etree.SubElement(root, 'Strings')
    etree.SubElement(strings_node, 'Section').text = "Story"

    texts_offset, pointers_offset = self.extract_story_pointers(tss, self.story_struct_byte_code, strings_offset,
                                                                pointer_block_size)

    print(texts_offset)
    person_offset = [self.extract_from_struct(tss, strings_offset, pointer_offset, struct_offset, root) for
                     pointer_offset, struct_offset in zip(pointers_offset, texts_offset)]

    # Create all the Nodes for Strings and grab the minimum offset
    # strings_node = etree.SubElement(root, 'Strings')
    # etree.SubElement(strings_node, 'Section').text = "Other Strings"
    # tss.seek(16)
    # texts_offset, pointers_offset = self.extract_story_pointers(tss, self.story_string_byte_code, strings_offset,
    #                                                            pointer_block_size)
    # [self.extract_from_string(tss, strings_offset, pointer_offset, text_offset, strings_node) for
    # pointer_offset, text_offset in zip(pointers_offset, texts_offset)]

    # text_start = min(min(person_offset, default=0), min(texts_offset, default=0))

    # Write the XML file
    txt = etree.tostring(root, encoding="UTF-8", pretty_print=True)
    with open(xml_path / f'{self.get_file_name(file_name)}.xml', "wb") as xmlFile:
        xmlFile.write(txt)
