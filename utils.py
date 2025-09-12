import os
import secrets
from datetime import datetime
from PIL import Image
from flask import current_app
import pandas as pd
from io import BytesIO
import openpyxl
from weasyprint import HTML
import logging
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_enrollment_number():
    """Generate unique enrollment number based on current datetime"""
    now = datetime.now()
    return f"ENR{now.strftime('%Y%m%d%H%M%S')}"

def save_logo(form_logo, centre_id):
    """Save uploaded logo file and return filename"""
    if not form_logo:
        return None

    try:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_logo.filename)
        picture_fn = f"logo_{centre_id}_{random_hex}{f_ext}"
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
        
        # Resize image while maintaining aspect ratio
        output_size = (200, 200)
        img = Image.open(form_logo)
        img.thumbnail(output_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if PNG
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        img.save(picture_path)
        return picture_fn
    except Exception as e:
        logger.error(f"Error saving logo: {str(e)}")
        return None

def calculate_net_fees(total_fees, concession):
    """Calculate net fees after applying concession"""
    try:
        concession = float(concession) if concession else 0
        total_fees = float(total_fees)
        return max(0, total_fees - concession)
    except (ValueError, TypeError):
        logger.error("Invalid fee calculation values")
        return total_fees

def export_students_excel(students, fields):
    """Export students data to Excel format"""
    try:
        data = []
        field_mapping = {
            'enrollment_number': 'Enrollment Number',
            'name': 'Student Name',
            'father_name': "Father's Name",
            'mobile1': 'Mobile Number',
            'course': 'Course',
            'total_fees': 'Total Fees (₹)',
            'net_fees': 'Net Fees (₹)',
            'paid_amount': 'Paid Amount (₹)',
            'balance_fees': 'Balance Fees (₹)',
            'fee_status': 'Fee Status',
            'date_of_joining': 'Joining Date'
        }

        for student in students:
            row = {}
            for field in fields:
                if field == 'course':
                    row[field_mapping[field]] = student.course.name if student.course else 'N/A'
                elif field == 'date_of_joining':
                    row[field_mapping[field]] = student.date_of_joining.strftime('%d-%m-%Y') if student.date_of_joining else ''
                elif field in ['total_fees', 'net_fees']:
                    row[field_mapping[field]] = float(student.__getattribute__(field))
                elif field == 'paid_amount':
                    row[field_mapping[field]] = float(student.get_total_paid())
                elif field == 'balance_fees':
                    row[field_mapping[field]] = float(student.get_balance_fees())
                elif field == 'fee_status':
                    row[field_mapping[field]] = student.get_fee_status()
                else:
                    row[field_mapping[field]] = student.__getattribute__(field) or ''
            data.append(row)
        
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
            worksheet = writer.sheets['Students']
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Excel export failed for students: {str(e)}")
        raise RuntimeError("Failed to generate Excel report for students")

def export_enquiries_excel(enquiries, fields):
    """Export enquiries data to Excel format"""
    try:
        data = []
        field_mapping = {
            'name': 'Name',
            'father_name': "Father's Name",
            'mobile1': 'Mobile Number',
            'course': 'Course Interested',
            'status': 'Status',
            'joining_plan': 'Joining Plan',
            'source_of_information': 'Source of Information'
        }

        for enquiry in enquiries:
            row = {}
            for field in fields:
                if field == 'course':
                    row[field_mapping[field]] = enquiry.course_interested.name if enquiry.course_interested else 'N/A'
                elif field == 'status':
                    row[field_mapping[field]] = enquiry.status.capitalize()
                else:
                    row[field_mapping[field]] = enquiry.__getattribute__(field) or ''
            data.append(row)
        
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Enquiries')
            worksheet = writer.sheets['Enquiries']
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Excel export failed for enquiries: {str(e)}")
        raise RuntimeError("Failed to generate Excel report for enquiries")

def export_students_pdf(students, fields, centre_name):
    """Export students data to PDF format with improved error handling"""
    try:
        # Field headers mapping
        field_headers = {
            'enrollment_number': 'Enrollment No.',
            'name': 'Student Name',
            'father_name': "Father's Name",
            'mobile1': 'Mobile',
            'course': 'Course',
            'total_fees': 'Total Fees (₹)',
            'net_fees': 'Net Fees (₹)',
            'paid_amount': 'Paid (₹)',
            'balance_fees': 'Balance (₹)',
            'fee_status': 'Status',
            'date_of_joining': 'Joining Date'
        }

        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Students Report - {centre_name}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 1cm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                    line-height: 1.5;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 16pt;
                    color: #333;
                }}
                .header .subtitle {{
                    font-size: 12pt;
                    color: #666;
                }}
                .report-info {{
                    margin-bottom: 10px;
                    font-size: 9pt;
                    color: #555;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    font-size: 9pt;
                }}
                th {{
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 6px;
                    text-align: left;
                    font-weight: bold;
                }}
                td {{
                    border: 1px solid #ddd;
                    padding: 6px;
                }}
                .footer {{
                    margin-top: 15px;
                    text-align: right;
                    font-size: 8pt;
                    color: #999;
                }}
                .numeric {{
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{centre_name}</h1>
                <div class="subtitle">Students Report</div>
            </div>
            
            <div class="report-info">
                Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')} | 
                Total Students: {len(students)}
            </div>
            
            <table>
                <thead>
                    <tr>
        """

        # Add table headers
        for field in fields:
            if field in field_headers:
                html_content += f"<th>{field_headers[field]}</th>"
        
        html_content += """
                    </tr>
                </thead>
                <tbody>
        """

        # Add student data rows
        for student in students:
            html_content += "<tr>"
            for field in fields:
                if field == 'course':
                    value = student.course.name if student.course else '-'
                    html_content += f"<td>{value}</td>"
                elif field == 'date_of_joining':
                    value = student.date_of_joining.strftime('%d-%m-%Y') if student.date_of_joining else '-'
                    html_content += f"<td>{value}</td>"
                elif field in ['total_fees', 'net_fees']:
                    value = f"₹{float(student.__getattribute__(field)):,.2f}"
                    html_content += f"<td class='numeric'>{value}</td>"
                elif field == 'paid_amount':
                    value = f"₹{float(student.get_total_paid()):,.2f}"
                    html_content += f"<td class='numeric'>{value}</td>"
                elif field == 'balance_fees':
                    value = f"₹{float(student.get_balance_fees()):,.2f}"
                    html_content += f"<td class='numeric'>{value}</td>"
                elif field == 'fee_status':
                    status = student.get_fee_status()
                    color = {
                        'Paid': 'color: green;',
                        'Partial': 'color: orange;',
                        'Unpaid': 'color: red;'
                    }.get(status, '')
                    html_content += f"<td style='{color}'>{status}</td>"
                else:
                    value = student.__getattribute__(field) or '-'
                    html_content += f"<td>{value}</td>"
            html_content += "</tr>"
        
        html_content += """
                </tbody>
            </table>
            
            <div class="footer">
                Generated by Lerzo | Page 1 of 1
            </div>
        </body>
        </html>
        """

        # Generate PDF
        pdf_output = BytesIO()
        HTML(string=html_content).write_pdf(pdf_output)
        pdf_output.seek(0)
        return pdf_output

    except Exception as e:
        logger.error(f"PDF generation failed for students: {str(e)}")
        raise RuntimeError("Failed to generate PDF report for students")

def export_enquiries_pdf(enquiries, fields, centre_name):
    """Export enquiries data to PDF format"""
    try:
        # Field headers mapping
        field_headers = {
            'name': 'Name',
            'father_name': "Father's Name",
            'mobile1': 'Mobile',
            'course': 'Course Interested',
            'status': 'Status',
            'joining_plan': 'Joining Plan',
            'source_of_information': 'Source of Information'
        }

        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Enquiries Report - {centre_name}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 1cm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                    line-height: 1.5;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 16pt;
                    color: #333;
                }}
                .header .subtitle {{
                    font-size: 12pt;
                    color: #666;
                }}
                .report-info {{
                    margin-bottom: 10px;
                    font-size: 9pt;
                    color: #555;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    font-size: 9pt;
                }}
                th {{
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 6px;
                    text-align: left;
                    font-weight: bold;
                }}
                td {{
                    border: 1px solid #ddd;
                    padding: 6px;
                }}
                .footer {{
                    margin-top: 15px;
                    text-align: right;
                    font-size: 8pt;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{centre_name}</h1>
                <div class="subtitle">Enquiries Report</div>
            </div>
            
            <div class="report-info">
                Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')} | 
                Total Enquiries: {len(enquiries)}
            </div>
            
            <table>
                <thead>
                    <tr>
        """

        # Add table headers
        for field in fields:
            if field in field_headers:
                html_content += f"<th>{field_headers[field]}</th>"
        
        html_content += """
                    </tr>
                </thead>
                <tbody>
        """

        # Add enquiry data rows
        for enquiry in enquiries:
            html_content += "<tr>"
            for field in fields:
                if field == 'course':
                    value = enquiry.course_interested.name if enquiry.course_interested else '-'
                    html_content += f"<td>{value}</td>"
                elif field == 'status':
                    status = enquiry.status.capitalize()
                    color = {
                        'Active': 'color: blue;',
                        'Converted': 'color: green;',
                        'Closed': 'color: red;'
                    }.get(status, '')
                    html_content += f"<td style='{color}'>{status}</td>"
                else:
                    value = enquiry.__getattribute__(field) or '-'
                    html_content += f"<td>{value}</td>"
            html_content += "</tr>"
        
        html_content += """
                </tbody>
            </table>
            
            <div class="footer">
                Generated by Lerzo | Page 1 of 1
            </div>
        </body>
        </html>
        """

        # Generate PDF - Updated to use newer WeasyPrint API
        pdf_output = BytesIO()
        HTML(string=html_content).write_pdf(pdf_output)
        pdf_output.seek(0)
        return pdf_output

    except Exception as e:
        logger.error(f"PDF generation failed for enquiries: {str(e)}")
        raise RuntimeError("Failed to generate PDF report for enquiries")

def generate_invoice_pdf(subscription_payment):
    """Generate invoice PDF for subscription payment"""
    try:
        # Generate invoice number
        invoice_number = f"INV-{subscription_payment.id:06d}"
        
        # Get centre details
        centre = subscription_payment.centre
        
        # HTML template with improved styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invoice {invoice_number}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 1.5cm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                    line-height: 1.5;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    color: #2c3e50;
                    margin: 0;
                    font-size: 18pt;
                }}
                .header .subtitle {{
                    color: #7f8c8d;
                    font-size: 12pt;
                }}
                .details-container {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }}
                .billing-details, .invoice-details {{
                    width: 48%;
                }}
                .section-title {{
                    font-size: 11pt;
                    font-weight: bold;
                    color: #2c3e50;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                    margin-bottom: 10px;
                }}
                .invoice-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .invoice-table th {{
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                .invoice-table td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
                .total-section {{
                    text-align: right;
                    margin-top: 20px;
                }}
                .total-amount {{
                    font-size: 12pt;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 10px;
                    border-top: 1px solid #eee;
                    font-size: 8pt;
                    color: #7f8c8d;
                    text-align: center;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 9pt;
                }}
                .status-completed {{
                    background-color: #d4edda;
                    color: #155724;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>INVOICE</h1>
                <div class="subtitle">TaskMasterPro Subscription</div>
            </div>
            
            <div class="details-container">
                <div class="billing-details">
                    <div class="section-title">Bill To:</div>
                    <p><strong>{centre.name}</strong></p>
                    <p>{centre.email}</p>
                    {f'<p>Phone: {centre.phone}</p>' if centre.phone else ''}
                    {f'<p>{centre.address}</p>' if centre.address else ''}
                    {f'<p>{centre.city}{f", {centre.pincode}" if centre.pincode else ""}</p>' if centre.city else ''}
                </div>
                
                <div class="invoice-details">
                    <div class="section-title">Invoice Details</div>
                    <p><strong>Invoice #:</strong> {invoice_number}</p>
                    <p><strong>Date:</strong> {subscription_payment.payment_date.strftime('%d-%m-%Y')}</p>
                    <p><strong>Payment ID:</strong> {subscription_payment.razorpay_payment_id}</p>
                    <p><strong>Status:</strong> <span class="status-badge status-completed">PAID</span></p>
                </div>
            </div>
            
            <table class="invoice-table">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Plan Type</th>
                        <th>Duration</th>
                        <th>Amount (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>TaskMasterPro Subscription</td>
                        <td>{subscription_payment.plan_type.capitalize()}</td>
                        <td>{'1 Month' if subscription_payment.plan_type == 'monthly' else '1 Year'}</td>
                        <td>{subscription_payment.amount:,.2f}</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="total-section">
                <p><strong>Subtotal: ₹{subscription_payment.amount:,.2f}</strong></p>
                <p><strong>Tax: ₹0.00</strong></p>
                <p class="total-amount">Total Amount: ₹{subscription_payment.amount:,.2f}</p>
            </div>
            
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>This is a computer-generated invoice and does not require a signature.</p>
                <p>For any questions, please contact support@taskmasterpro.com</p>
            </div>
        </body>
        </html>
        """

        # Generate PDF
        pdf_output = BytesIO()
        HTML(string=html_content).write_pdf(pdf_output)
        pdf_output.seek(0)
        
        return pdf_output, invoice_number

    except Exception as e:
        logger.error(f"Invoice generation failed: {str(e)}")
        raise RuntimeError("Failed to generate invoice")

def calculate_trial_end_date():
    """Calculate trial end date (14 days from now)"""
    return datetime.now() + timedelta(days=14)

def format_currency(amount):
    """Format amount as currency"""
    try:
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"