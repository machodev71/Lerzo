import os
import secrets
from datetime import datetime
from PIL import Image
from flask import current_app
import pandas as pd
from io import BytesIO
import openpyxl
from weasyprint import HTML, CSS

def generate_enrollment_number():
    """Generate unique enrollment number based on current datetime"""
    now = datetime.now()
    return f"ENR{now.strftime('%Y%m%d%H%M%S')}"

def save_logo(form_logo, centre_id):
    """Save uploaded logo file and return filename"""
    if form_logo:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_logo.filename)
        picture_fn = f"logo_{centre_id}_{random_hex}{f_ext}"
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
        
        # Resize image
        output_size = (200, 200)
        img = Image.open(form_logo)
        img.thumbnail(output_size)
        img.save(picture_path)
        
        return picture_fn
    return None

def export_students_excel(students, fields):
    """Export students data to Excel format"""
    data = []
    for student in students:
        row = {}
        if 'enrollment_number' in fields:
            row['Enrollment Number'] = student.enrollment_number
        if 'name' in fields:
            row['Name'] = student.name
        if 'father_name' in fields:
            row['Father Name'] = student.father_name
        if 'mobile1' in fields:
            row['Mobile 1'] = student.mobile1
        if 'course' in fields:
            row['Course'] = student.course.name if student.course else ''
        if 'total_fees' in fields:
            row['Total Fees'] = student.total_fees
        if 'net_fees' in fields:
            row['Net Fees'] = student.net_fees
        if 'paid_amount' in fields:
            row['Paid Amount'] = student.get_total_paid()
        if 'balance_fees' in fields:
            row['Balance Fees'] = student.get_balance_fees()
        if 'fee_status' in fields:
            row['Fee Status'] = student.get_fee_status()
        if 'date_of_joining' in fields:
            row['Date of Joining'] = student.date_of_joining.strftime('%Y-%m-%d') if student.date_of_joining else ''
        
        data.append(row)
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Students')
    output.seek(0)
    
    return output

def export_students_pdf(students, fields, centre_name):
    """Export students data to PDF format"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Students Report - {centre_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ text-align: center; color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Students Report - {centre_name}</h1>
        <table>
            <thead>
                <tr>
    """
    
    # Add headers
    if 'enrollment_number' in fields:
        html_content += "<th>Enrollment Number</th>"
    if 'name' in fields:
        html_content += "<th>Name</th>"
    if 'father_name' in fields:
        html_content += "<th>Father Name</th>"
    if 'mobile1' in fields:
        html_content += "<th>Mobile 1</th>"
    if 'course' in fields:
        html_content += "<th>Course</th>"
    if 'total_fees' in fields:
        html_content += "<th>Total Fees</th>"
    if 'net_fees' in fields:
        html_content += "<th>Net Fees</th>"
    if 'paid_amount' in fields:
        html_content += "<th>Paid Amount</th>"
    if 'balance_fees' in fields:
        html_content += "<th>Balance Fees</th>"
    if 'fee_status' in fields:
        html_content += "<th>Fee Status</th>"
    if 'date_of_joining' in fields:
        html_content += "<th>Date of Joining</th>"
    
    html_content += "</tr></thead><tbody>"
    
    # Add data rows
    for student in students:
        html_content += "<tr>"
        if 'enrollment_number' in fields:
            html_content += f"<td>{student.enrollment_number}</td>"
        if 'name' in fields:
            html_content += f"<td>{student.name}</td>"
        if 'father_name' in fields:
            html_content += f"<td>{student.father_name or ''}</td>"
        if 'mobile1' in fields:
            html_content += f"<td>{student.mobile1}</td>"
        if 'course' in fields:
            html_content += f"<td>{student.course.name if student.course else ''}</td>"
        if 'total_fees' in fields:
            html_content += f"<td>₹{student.total_fees:.2f}</td>"
        if 'net_fees' in fields:
            html_content += f"<td>₹{student.net_fees:.2f}</td>"
        if 'paid_amount' in fields:
            html_content += f"<td>₹{student.get_total_paid():.2f}</td>"
        if 'balance_fees' in fields:
            html_content += f"<td>₹{student.get_balance_fees():.2f}</td>"
        if 'fee_status' in fields:
            html_content += f"<td>{student.get_fee_status()}</td>"
        if 'date_of_joining' in fields:
            html_content += f"<td>{student.date_of_joining.strftime('%Y-%m-%d') if student.date_of_joining else ''}</td>"
        html_content += "</tr>"
    
    html_content += "</tbody></table></body></html>"
    
    # Generate PDF
    pdf_output = BytesIO()
    HTML(string=html_content).write_pdf(pdf_output)
    pdf_output.seek(0)
    
    return pdf_output

def calculate_net_fees(total_fees, concession):
    """Calculate net fees after applying concession"""
    return total_fees - (concession or 0)

def generate_invoice_pdf(subscription_payment):
    """Generate invoice PDF for subscription payment"""
    from flask import render_template_string
    from datetime import datetime
    import io
    
    # Generate invoice number
    invoice_number = f"INV-{subscription_payment.id:06d}"
    
    # Invoice template
    invoice_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Invoice {{ invoice_number }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .header { text-align: center; border-bottom: 2px solid #0d6efd; padding-bottom: 20px; margin-bottom: 30px; }
            .company-name { font-size: 24px; font-weight: bold; color: #0d6efd; }
            .invoice-title { font-size: 20px; margin-top: 10px; }
            .invoice-details { display: flex; justify-content: space-between; margin-bottom: 30px; }
            .billing-details, .invoice-info { width: 48%; }
            .billing-details h4, .invoice-info h4 { margin-bottom: 10px; color: #333; }
            .table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
            .table th, .table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            .table th { background-color: #f8f9fa; font-weight: bold; }
            .total-section { text-align: right; margin-top: 20px; }
            .total-amount { font-size: 18px; font-weight: bold; color: #0d6efd; }
            .footer { margin-top: 50px; text-align: center; font-size: 12px; color: #666; }
            .payment-status { display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
            .status-completed { background-color: #d1e7dd; color: #0f5132; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-name">Student Management System</div>
            <div class="invoice-title">SUBSCRIPTION INVOICE</div>
        </div>
        
        <div class="invoice-details">
            <div class="billing-details">
                <h4>Bill To:</h4>
                <p><strong>{{ centre_name }}</strong></p>
                <p>{{ centre_email }}</p>
                {% if centre_phone %}
                <p>Phone: {{ centre_phone }}</p>
                {% endif %}
                {% if centre_address %}
                <p>{{ centre_address }}</p>
                {% endif %}
                {% if centre_city %}
                <p>{{ centre_city }}{% if centre_pincode %} - {{ centre_pincode }}{% endif %}</p>
                {% endif %}
            </div>
            
            <div class="invoice-info">
                <h4>Invoice Details:</h4>
                <p><strong>Invoice Number:</strong> {{ invoice_number }}</p>
                <p><strong>Date:</strong> {{ payment_date }}</p>
                <p><strong>Payment ID:</strong> {{ payment_id }}</p>
                <p><strong>Status:</strong> <span class="payment-status status-completed">{{ status.upper() }}</span></p>
            </div>
        </div>
        
        <table class="table">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Plan Type</th>
                    <th>Duration</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Student Management System Subscription</td>
                    <td>{{ plan_type.title() }}</td>
                    <td>{{ duration }}</td>
                    <td>₹{{ "%.2f"|format(amount) }}</td>
                </tr>
            </tbody>
        </table>
        
        <div class="total-section">
            <p><strong>Subtotal: ₹{{ "%.2f"|format(amount) }}</strong></p>
            <p><strong>Tax: ₹0.00</strong></p>
            <p class="total-amount">Total Amount: ₹{{ "%.2f"|format(amount) }}</p>
        </div>
        
        <div class="footer">
            <p>Thank you for your business!</p>
            <p>This is a computer-generated invoice and does not require a signature.</p>
            <p>For any queries, please contact support.</p>
        </div>
    </body>
    </html>
    """
    
    # Prepare template data
    centre = subscription_payment.centre
    template_data = {
        'invoice_number': invoice_number,
        'centre_name': centre.name,
        'centre_email': centre.email,
        'centre_phone': centre.phone,
        'centre_address': centre.address,
        'centre_city': centre.city,
        'centre_pincode': centre.pincode,
        'payment_date': subscription_payment.payment_date.strftime('%d %B %Y'),
        'payment_id': subscription_payment.razorpay_payment_id,
        'status': subscription_payment.status,
        'plan_type': subscription_payment.plan_type,
        'duration': '1 Month' if subscription_payment.plan_type == 'monthly' else '1 Year',
        'amount': subscription_payment.amount
    }
    
    # Render template
    html_content = render_template_string(invoice_template, **template_data)
    
    # Generate PDF
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file, invoice_number
