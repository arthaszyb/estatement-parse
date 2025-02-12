import re
import io

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

#citibank_regex = r"(\d{2}\s[A-Z]{3})\s+(.*?)\s+([\d,\.]+)\s*$"
citibank_regex = r"\$?([\d,]+\.\d{2})"  # Match amounts like $46,100.00 or 588.42



transactions = []
for line in io.StringIO(citibank_ocr_text):
    match = re.search(citibank_regex, line)
    if match:
        date = match.group(1)
        description = match.group(2).strip()
        amount_str = match.group(3).replace(",", "")
        amount = float(amount_str)
        transactions.append({
            "Date": date,
            "Description": description,
            "Amount SGD": amount
        })

for transaction in transactions:
    print(transaction)