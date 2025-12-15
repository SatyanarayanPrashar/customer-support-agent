BILLING_TOOLS_SCHEMA = [
    {
        "type": "function",
        "name": "get_bills",
        "description": "Retrieve all bills associated with a phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "ph_number": {
                    "type": "integer",
                    "description": "The customer's phone number."
                }
            },
            "required": ["ph_number"]
        }
    },
    {
        "type": "function",
        "name": "get_bill_by_id",
        "description": "Retrieve a particular bill by its ID for a given phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "ph_number": {
                    "type": "integer",
                    "description": "The customer's phone number."
                },
                "bill_id": {
                    "type": "string",
                    "description": "The unique identifier of the bill."
                }
            },
            "required": ["ph_number", "bill_id"]
        }
    },
    {
        "type": "function",
        "name": "send_bill",
        "description": "Send a bill to the customer via the specified mode.",
        "parameters": {
            "type": "object",
            "properties": {
                "ph_number": {
                    "type": "integer",
                    "description": "The customer's phone number."
                },
                "bill_id": {
                    "type": "string",
                    "description": "The unique identifier of the bill."
                },
                "mode": {
                    "type": "string",
                    "description": "The mode of sending the bill (e.g., Email, SMS, UPI)."
                }
            },
            "required": ["ph_number", "bill_id", "mode"]
        }
    },
    {
        "type": "function",
        "name": "refund_ticket",
        "description": "Process a refund ticket for a specific bill.",
        "parameters": {
            "type": "object",
            "properties": {
                "ph_number": {
                    "type": "integer",
                    "description": "The customer's phone number."
                },
                "bill_id": {
                    "type": "string",
                    "description": "The unique identifier of the bill."
                },
                "amount": {
                    "type": ["number", "string"],
                    "description": "The amount to be refunded."
                },
                "reason": {
                    "type": "string",
                    "description": "The reason for the refund."
                }
            },
            "required": ["ph_number", "bill_id", "amount", "reason"]
        }
    }
]

def get_bills(ph_number: int):
    """
    Returns all the bills associated with a phone number.
    This is mock data — same bill returned regardless of phone number.
    Each bill can include multiple products with individual prices and a total.
    """
    bills = [
        {
            "ph_number": str(ph_number),
            "name": "John Doe",
            "user_id": "U123456",
            "bills": [
                {
                    "bill_id": "B001",
                    "due_date": "2024-07-15",
                    "mode": "UPI",
                    "total_amount": 299.97,
                    "items": [
                        {"product": "Robotic Floor Cleaner M612", "price": 249.99},
                        {"product": "Cleaner Solution (1L)", "price": 19.99},
                        {"product": "Replacement Mop Pads (Pack of 3)", "price": 29.99},
                    ],
                },
                {
                    "bill_id": "B002",
                    "due_date": "2024-09-05",
                    "mode": "Credit Card",
                    "total_amount": 488.23,
                    "items": [
                        {"product": "Robotic Floor Cleaner M612", "price": 249.99},
                        {"product": "Dust Filter Cartridge", "price": 15.49},
                        {"product": "Mop Head Replacement Kit", "price": 22.75},
                    ],
                }
            ]
        }
    ]

    return bills

def get_bill_by_id(ph_number: int, bill_id: str):
    """
    Retrieve a particular bill by its ID for the given phone number.
    Returns None if no matching bill is found.
    """
    all_bills = get_bills(ph_number)
    customer = all_bills[0]  # Since this is mock data, only one customer entry

    for bill in customer["bills"]:
        if bill["bill_id"].lower() == bill_id.lower():
            return {
                "ph_number": customer["ph_number"],
                "name": customer["name"],
                "bill": bill
            }

    return None

def send_bill(ph_number: int, bill_id: str, mode: str):
    """
    Mock function to simulate sending a bill to the customer.
    Returns a success message.
    """
    # In a real implementation, this would integrate with an email/SMS service
    return f"Bill {bill_id} has been sent to phone number {ph_number} via {mode}."

def refund_ticket(ph_number: int, bill_id: str, amount, reason: str):
    """
    Mock function to simulate processing a refund.
    Returns a success message.
    """
    if isinstance(amount, str):
        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount provided. Please enter a numeric value."
    if amount is None or amount == 0 or amount < 0:
        return "Please calculate the refund amount before raising a refund ticket."
    return f"A refund ticket of ${amount:.2f} for bill {bill_id} has been raised for phone number {ph_number} due to '{reason}'."

BILLING_TOOL_MAP = {
    "get_bills": get_bills,
    "get_bill_by_id": get_bill_by_id,
    "send_bill": send_bill,
    "refund_ticket": refund_ticket
}