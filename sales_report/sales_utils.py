from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from django.core.mail import EmailMessage

def generate_invoice(order):
    # Create a BytesIO buffer to hold the PDF
    buffer = BytesIO()

    # Create a canvas object for PDF generation
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # page size

    # Add the logo (ensure the path is correct, and the logo is available in your static files)
    logo_path = settings.BASE_DIR / 'static' / 'img' / 'logo.png'  # Update this path as needed
    c.drawImage(str(logo_path), 30, height - 60, width=100, height=40)  # Adjust logo position and size

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkblue)
    c.drawString(200, height - 40, f"Invoice - Order #{order.order_id}")

    # Customer details section
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(30, height - 80, f"Customer: ")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 80, f"{order.user.get_full_name()}")
    c.drawString(100, height - 100, f"Email: {order.user.email}")

    # Order details
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(30, height - 140, f"Order Date: {order.created_at.strftime('%d-%b-%Y')}")
    c.drawString(30, height - 160, f"Total Amount: INR {order.final_price}")

    # Draw a line to separate the sections
    c.setStrokeColor(colors.lightgrey)  # Corrected color name
    c.setLineWidth(0.5)
    c.line(30, height - 170, width - 30, height - 170)

    # Table header for items
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.darkblue)
    c.rect(30, height - 200, width - 60, 20, fill=True)
    c.setFillColor(colors.white)
    c.drawString(40, height - 195, "Product")
    c.drawString(200, height - 195, "Quantity")
    c.drawString(300, height - 195, "Price")
    c.drawString(400, height - 195, "Total")

    # Draw table row lines and display order items
    y_position = height - 220
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)

    for item in order.items.all():
        c.drawString(40, y_position, item.variant.product.name)
        c.drawString(200, y_position, str(item.quantity))
        c.drawString(300, y_position, f"INR {item.variant.price:.2f}")
        c.drawString(400, y_position, f"INR {item.quantity * item.variant.price:.2f}")
        y_position -= 20
        c.line(30, y_position + 5, width - 30, y_position + 5)  # row separator

    # Footer with payment info
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.darkblue)
    c.drawString(30, y_position - 20, f"Thank you for shopping with us!")
    c.setFont("Helvetica", 10)
    c.drawString(30, y_position - 40, f"Payment Method: {order.payment_details.payment_method}")
    
    # Save the PDF to the buffer
    c.save()

    # Get the value of the BytesIO buffer and return it in the HTTP response
    buffer.seek(0)
    
    # Create HTTP response with the PDF as attachment
    response = HttpResponse(buffer, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    return response

# Send email with invoice
def send_invoice_email(order):
    # Generate the PDF invoice
    invoice_pdf = generate_invoice(order)

    # Create email message
    subject = f"Invoice for Order #{order.order_id}"
    message = f"Dear {order.user.get_full_name()},\n\nThank you for your order. Please find attached your invoice for order #{order.order_id}.\n\nBest regards,\n OPTINOVA"
    
    # Email recipient and sender
    to_email = order.user.email
    from_email = settings.DEFAULT_FROM_EMAIL

    # Create an email message
    email = EmailMessage(subject, message, from_email, [to_email])
    email.attach(f"invoice_{order.order_id}.pdf", invoice_pdf.getvalue(), 'application/pdf')
    email.send()