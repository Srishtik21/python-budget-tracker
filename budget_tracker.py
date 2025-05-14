def show_menu():
    print("\n=== Budget Tracker Menu ===")
    print("1. Add Income")
    print("2. Add Expense")
    print("3. Show balance")
    print("4. Sow Transations")
    print("5. Exit")

balance=0
transaction=[]

def add_income():
    global balance
    amount =float(input("Enter income amount: "))
    balance+=amount
    transaction.append(f"Income: +Rs.{amount}")

def add_expense():
    global balance
    amount=float(input("Enter expense amount: "))
    balance-=amount
    transaction.append(f"Expense: -Rs.{amount}")

def show_balance():
    print(f"Current Balance: Rs.{balance}")

def show_transaction():
    print("--- Transaction History ---")
    for t in transaction:
        print(t)

while True:
    show_menu()
    choice=input("Enter your choice: ")

    if choice=="1":
        add_income()
    elif choice=="2":
        add_expense()
    elif choice=="3":
        show_balance()
    elif choice=="4":
        show_transaction()
    elif choice=="5":
        print("Exiting...")
        break
    else:
        print("Invalid choice. Try again.")

