a='Payment Due Date January 09, 2025'

import re
from datetime import datetime

regex=r"(\w{3,9})\s(\d{2}),\s(\d{4})"
regex1=r"[Dd]ue\s+Date\s*([A-Za-z]{3,8}\s*\d{1,2}\,?\s*\d{4})"

match=re.search(regex,a)
match1=re.search(regex1,a)
print(match.group(1))
print(match1.group(1))

dt = datetime.strptime(match1.group(1), "%B %d, %Y").date()