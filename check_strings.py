import os
import re

def find_vietnamese_strings(directory):
    vietnamese_chars = re.compile(r'[àáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹýÀÁÃẠẢĂẮẰẲẴẶÂẤẦẨẪẬÈÉẸẺẼÊỀẾỂỄỆĐÌÍĨỈỊÒÓÕỌỎÔỐỒỔỖỘƠỚỜỞỠỢÙÚŨỤỦƯỨỪỬỮỰỲỴỶỸÝ]')
    
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.tsx') or file.endswith('.ts'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find strings in quotes or JSX text
                    # For simplicity, we just look line by line and see if it contains Vietnamese chars but not inside t()
                    for line in content.splitlines():
                        if vietnamese_chars.search(line):
                            if 't(' not in line and 'console.' not in line and '//' not in line:
                                count += 1
    return count

print("Approx lines with Vietnamese strings outside t():", find_vietnamese_strings('apps/web/src'))
