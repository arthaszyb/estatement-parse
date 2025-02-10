import re
import io

citibank_ocr_text = """
0
Citibank
Statement of Account
609775 0005425503004517776
(609775L)
YANG ZHOU,
37 JURONG EAST AVENUE 1
#10-03
SINGAPORE 609775
000872J/AA
This Statement serves as a Tax Invoice if GST is charged.
YOUR CITIBANK CARDS
CITI REWARDS WORLD MASTERCARD
cíti
Citibank Singapore Ltd
Robinson Road P. O. Box 355 S(900705)
Page 1 of 6
YOUR BILL SUMMARY
Statement Date
Credit Limit
Current Balance
Total Minimum Payment
Payment Due Date
November 15, 2024
$46,100.00
$588.42
$50.00
December 10, 2024
GST Registration No. MR85002419
CURRENT
BALANCE
AMOUNT
PAST DUE
588.42
0.00
MINIMUM
PAYMENT
50.00
REWARD
PROGRAMME
POINTS
TOTAL POINTS
AVAILABLE
3,141
Detailed transactions can be found on the following pages.
If you have more than one Citibank credit card and receive separate statements of account for these cards (i) you will need to aggregate the Current Balance and Total Minimum amounts in
these statements to determine your Current Balance and Total Minimum Payment amounts across all your Credit Card accounts and (ii) your Overlimit Amount across all Card accounts will only
be reflected in one of these statements. Accordingly, you should read these statements together.
Please settle this statement promptly (the minimum payment required is stated in the table above). If the Minimum Payment Amount is not received by Payment Due Date, a late charge (if
applicable) will be levied. If the payment of the Current Balance (including any billed instalments) is not made in full by the Payment Due Date, daily interest will be assessed at an effective
interest rate from each transaction date on all transactions/charges in this statement and all transactions/charges posted after this statement date. (Please refer to the back of this statement for
full details)
Please examine this statement immediately. If no discrepancy is reported within 10 days from the date of this statement, the information on this statement of account will be considered as correct
subject to our right to rectify as set out in the cardmember's agreement.
Note: The Current Balance indicated on the payment stub is computed on the sum of Debit Balances only. All Credit Balances are excluded from this calculation.
PAYMENT SLIP
YANG ZHOU,
CREDIT CARD TYPE
CITI REWARDS
WORLD MASTERCARD
ACCOUNT NUMBER
CURRENT BALANCE $
5425503004517776
588.42
Statement Date: November 15, 2024
Payment Due Date: December 10, 2024
MINIMUM PAYMENT $
50.00
PAYMENT AMOUNT $
TOTAL FOR THE CARD(S) ABOVE
Please make your payment before the payment due date.
588.42
50.00
Make payment more conveniently and almost instantly via FAST (Fast and Secure Transfer) with your other bank's account. Find out more at www.citibank.com.sg/FAST.
If you are paying by check, make the check payable to "Citibank Singapore Ltd" and write all your Account Numbers on the back of the check. Do not send postdated
checks. Use the Business Reply Envelope (download at www.citibank.com.sg/bre) for check payment.
Please note minimum payment amount does not include any overlimit amount. If you are over limit, please arrange to pay the overlimit amount in addition to total minimum
payment amount.
Please clearly indicate your payment amount for each account above. If left unspecified, we will apply our discretion to appropriate all payments received by us in such manner
and order of priority as we may deem fit.
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