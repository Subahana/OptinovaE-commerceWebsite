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
    width, height = letter  # Page size

    # Header: Clean, minimalistic design with accent color
    logo_path = settings.BASE_DIR / 'static' / 'img' / 'logo.png'  # Update this path as needed
    c.setFillColor(colors.lightblue)
    c.rect(0, height - 120, width, 120, fill=True)  # Light header background color
    c.drawImage(str(logo_path), 30, height - 100, width=120, height=50)  # Logo size and position

    # Title: Elegant company name with modern typography
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.darkblue)
    c.drawString(160, height - 80, "Optinove")  # Company name

    # Customer details section with modern styling and whitespace
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkblue)
    c.drawString(30, height - 160, "Customer Information")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawString(30, height - 180, f"Name: {order.user.get_full_name()}")
    c.drawString(30, height - 200, f"Email: {order.user.email}")
    c.drawString(30, height - 220, f"Shipping Address: {order.address}")

    # Order details with modern typography and alignment
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, height - 260, "Order Details")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 280, f"Order Date: {order.created_at.strftime('%d-%b-%Y')}")
    c.drawString(30, height - 300, f"Total Amount: INR {order.final_price:.2f}")
    c.drawString(30, height - 320, f"Invoice for Order #{order.order_id}")

    # Draw a soft line separating sections
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.line(30, height - 330, width - 30, height - 330)

    # Table header with bold font and accent color
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.darkblue)
    c.drawString(40, height - 375, "Product")
    c.drawString(220, height - 375, "Quantity")
    c.drawString(320, height - 375, "Price (INR)")
    c.drawString(420, height - 375, "Total (INR)")

    # Draw table rows with alternating colors for readability
    y_position = height - 400
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)

    row_color = colors.whitesmoke  # Starting row color
    for item in order.items.all():
        # Draw a colored row for each item
        c.setFillColor(row_color)
        c.rect(30, y_position - 5, width - 60, 20, fill=True)  # Row background color
        c.setFillColor(colors.black)

        # Draw item details in the table
        c.drawString(40, y_position, item.variant.product.name)
        c.drawString(220, y_position, str(item.quantity))
        c.drawString(320, y_position, f"INR {item.variant.price:.2f}")
        c.drawString(420, y_position, f"INR {item.quantity * item.variant.price:.2f}")

        y_position -= 25  # Move to the next row
        c.line(30, y_position + 5, width - 30, y_position + 5)  # Row separator line

        # Alternate row colors for better readability
        row_color = colors.white if row_color == colors.whitesmoke else colors.whitesmoke

    # Footer: Stylish and minimal message with payment info
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.darkblue)
    c.drawString(30, y_position - 40, "Thank you for shopping with us!")
    c.setFont("Helvetica", 10)
    c.drawString(30, y_position - 60, f"Payment Method: {order.payment_details.payment_method}")

    # Add a note about customer support or policy in an italic font
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(30, y_position - 80, "For inquiries, contact support@example.com")

    # Closing line to wrap the document
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.line(30, y_position - 100, width - 30, y_position - 100)

    # Save the PDF to the buffer
    c.save()

    # Get the value of the BytesIO buffer and return it in the HTTP response
    buffer.seek(0)

    # Create HTTP response with the PDF as attachment
    response = HttpResponse(buffer, content_type="application/pdf")
    response['Content-Disposition'] = f'inline; filename="invoice_{order.order_id}.pdf"'
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