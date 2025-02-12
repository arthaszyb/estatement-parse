import re
from datetime import datetime
from typing import Optional

citibank_ocr_text = """
6777154003055245
CitibankSingaporeLtd
RobinsonRoadP.O.Box355S(900705)
YOURBILLSUMMARY
6113370005425503004517776
StatementDate January15,2025
CreditLimit $46,100.00
YANGZHOU,
CurrentBalance $3,593.10
337A,TAHCHINGROAD
#17-45 TotalMinimum Payment $50.00
SG611337
PaymentDueDate February10,2025
GSTRegistrationNo.MR85002419
ThisStatementservesasaTaxInvoiceifGSTischarged.
Detailedtransactionscanbefoundonthefollowingpages.
IfyouhavemorethanoneCitibankcreditcardandreceiveseparatestatementsofaccountforthesecards(i)youwillneedtoaggregatetheCurrentBalanceandTotalMinimumamountsin
thesestatementstodetermineyourCurrentBalanceandTotalMinimumPaymentamountsacrossallyourCreditCardaccountsand(ii)yourOverlimitAmountacrossallCardaccountswillonly
bereflectedinoneofthesestatements.Accordingly,youshouldreadthesestatementstogether.
Pleasesettlethisstatementpromptly(theminimumpaymentrequiredisstatedinthetableabove).IftheMinimumPaymentAmountisnotreceivedbyPaymentDueDate,alatecharge(if
applicable)willbelevied.IfthepaymentoftheCurrentBalance(includinganybilledinstalments)isnotmadeinfullbythePaymentDueDate,dailyinterestwillbeassessedataneffective
interestratefromeachtransactiondateonalltransactions/chargesinthisstatementandalltransactions/chargespostedafterthisstatementdate.(Pleaserefertothebackofthisstatementfor
fulldetails)
Pleaseexaminethisstatementimmediately.Ifnodiscrepancyisreportedwithin10daysfromthedateofthisstatement,theinformationonthisstatementofaccountwillbeconsideredascorrect
subjecttoourrighttorectifyassetoutinthecardmember'sagreement.
Note:TheCurrentBalanceindicatedonthepaymentstubiscomputedonthesumofDebitBalancesonly.AllCreditBalancesareexcludedfromthiscalculation.
0001
(6113378)
K584903002:oNgeRoC
Page1 of6
Pleasemakeyourpaymentbeforethepaymentduedate.
MakepaymentmoreconvenientlyandalmostinstantlyviaFAS
"""

class Retest:
    @staticmethod
    def extract_statement_date(text: str) -> Optional[datetime.date]:
        # Example: "Payment Due Date January 09, 2025"
        # Also may be "Payment Due Date : 09 Feb 2025", so need multiple patterns
        patterns = [
            r"[Dd]ue\s*Date\s*:?\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"[Dd]ue\s*Date\s*([A-Za-z]{3,8}\s*\d{1,2}\,?\s*\d{4})"
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                date_str = m.group(1)
                print(f"Found statement date string: {date_str}")
                # Possible formats: "January 09, 2025" or "Jan 09 2025", etc.
                possible_formats = ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %b %Y"]
                for fmt in possible_formats:
                    try:
                        dt_obj = datetime.strptime(date_str.strip(), fmt).date()
                        print(f"Parsed statement date with format '{fmt}': {dt_obj}")
                        return dt_obj  # Return a date object
                    except ValueError:
                        continue
                print(f"Failed to parse statement date with known formats: {date_str}")
        return None

# Use the static method directly
date_result = Retest.extract_statement_date(citibank_ocr_text)
print(date_result)