#!/usr/bin/env python3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Create test PO PDF
pdf_path = "test_po.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)
width, height = letter

# Header
c.setFont("Helvetica-Bold", 16)
c.drawString(1*inch, height - 1*inch, "PURCHASE ORDER")

# PO info
c.setFont("Helvetica", 12)
c.drawString(1*inch, height - 1.5*inch, "PO Number: PO-2024-001")
c.drawString(1*inch, height - 1.8*inch, "Vendor: Acme Corporation")
c.drawString(1*inch, height - 2.1*inch, "Date: 2024-03-01")

# Line items table
y = height - 3*inch
c.setFont("Helvetica-Bold", 10)
c.drawString(1*inch, y, "Item Description")
c.drawString(3.5*inch, y, "Quantity")
c.drawString(4.5*inch, y, "Unit Price")
c.drawString(5.5*inch, y, "Total")

c.setFont("Helvetica", 10)
y -= 0.3*inch
c.drawString(1*inch, y, "Widget A")
c.drawString(3.5*inch, y, "10")
c.drawString(4.5*inch, y, "$50.00")
c.drawString(5.5*inch, y, "$500.00")

y -= 0.3*inch
c.drawString(1*inch, y, "Widget B")
c.drawString(3.5*inch, y, "5")
c.drawString(4.5*inch, y, "$100.00")
c.drawString(5.5*inch, y, "$500.00")

y -= 0.3*inch
c.drawString(1*inch, y, "Widget C")
c.drawString(3.5*inch, y, "10")
c.drawString(4.5*inch, y, "$50.00")
c.drawString(5.5*inch, y, "$500.00")

# Total
y -= 0.5*inch
c.setFont("Helvetica-Bold", 12)
c.drawString(4.5*inch, y, "Total: $1500.00")

c.save()
print(f"Created {pdf_path}")

# Now test extracting text from it
import pdfplumber

with pdfplumber.open(pdf_path) as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"

print("\nExtracted text:")
print("=" * 60)
print(text)
print("=" * 60)
