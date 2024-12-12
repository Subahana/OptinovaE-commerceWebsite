from .models import Wallet, WalletTransaction
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def ensure_wallet_exists(user):
    """
    Ensures the given user has a wallet. Creates one if it does not exist.
    """
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet


def credit_wallet(user, amount, description=""):
    if amount <= 0:
        raise ValueError("Credit amount must be positive.")

    wallet = Wallet.objects.get_or_create(user=user)[0]
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='credit',
        amount=Decimal(amount),
        description=description
    )
    return wallet.balance


def debit_wallet(user, amount, description):
    # Ensure the amount is a Decimal for consistency
    amount = Decimal(amount)
    
    # Access the wallet directly since it's created with the user signal
    wallet = user.wallet

    # Check if the wallet balance is sufficient
    if wallet.balance < amount:
        raise ValueError("Insufficient balance in wallet.")

    # Create the debit transaction
    WalletTransaction.objects.create(
        wallet=wallet,  # Link the wallet to the transaction
        transaction_type='debit',
        amount=amount,
        description=description
    )

def process_refund_to_wallet(order):
    """
    Process the refund for an order. Ensures that refund happens only when necessary.
    """
    # Access the payment status string from the PaymentStatus object
    payment_status = getattr(order.payment_details.payment_status, 'status', '').strip().lower()
    print(f"Raw Payment Status: '{payment_status}'")
    
    # Check if the order has been paid successfully and is not already refunded
    if payment_status != 'completed':
        raise Exception("Refund can only be processed for paid orders.")
    
    # Ensure the order has not already been refunded
    if payment_status == 'refund':
        raise Exception("Refund has already been processed for this order.")
    
    # Calculate the refund amount
    refund_amount = calculate_refund_amount(order)

    # Ensure the refund amount is positive
    if refund_amount <= 0:
        raise ValueError("Refund amount must be positive.")

    # Log the refund process
    logger.debug(f"Processing refund for Order ID {order.id}, Refund Amount: {refund_amount}")

    # Access or create the user's wallet
    user_wallet = ensure_wallet_exists(order.user)

    # Add the refund amount to the user's wallet balance
    user_wallet.balance += refund_amount
    user_wallet.save()

    # Log the transaction
    WalletTransaction.objects.create(
        wallet=user_wallet,
        transaction_type="refund",
        amount=refund_amount,
        description=f"Refund for Order ID {order.id}"
    )
    logger.info(f"Refund of {refund_amount} successfully processed for Order ID {order.id}.")


def calculate_refund_amount(order):
    """
    Calculate the refund amount for the given order.
    Ensures that the refund amount is positive.
    """
    total_amount = getattr(order, 'final_price', 0)  # Ensure this field holds the order's total value

    if total_amount <= 0:
        raise ValueError("Refund amount must be positive.")
    
    return total_amount

