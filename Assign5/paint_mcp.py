from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mcp import types
from PIL import Image as PILImage
import math
import sys
from pywinauto.application import Application
import win32gui
import win32con
import time
from win32api import GetSystemMetrics
import pyautogui
import time
import subprocess
import os
from dotenv import load_dotenv

#load env
load_dotenv()
# instantiate an MCP server client
mcp = FastMCP("Mspaint")

#Intializing tools
@mcp.tool()
async def show_reasoning(steps: list) -> TextContent:
    """Show the step-by-step reasoning process"""
    print("[blue]FUNCTION CALL:[/blue] show_reasoning()")
    for i, step in enumerate(steps, 1):
        print(f"Step {i}:{step}")
    return TextContent(
        type="text",
        text="Reasoning shown"
    )

@mcp.tool()
async def verify_calculation(expression: str, expected: float) -> TextContent:
    """Verify if a calculation is correct"""
    print("[blue]FUNCTION CALL:[/blue] verify()")
    print(f"[blue]Verifying:[/blue] {expression} = {expected}")
    try:
        actual = float(eval(expression))
        is_correct = abs(actual - float(expected)) < 1e-10
        
        if is_correct:
            print(f"Correct! {expression} = {expected}[/green]")
        else:
            print(f"Incorrect! {expression} should be {actual}, got {expected}[/red]")
            
        return TextContent(
            type="text",
            text=str(is_correct)
        )
    except Exception as e:
        print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )
    
@mcp.tool()
async def verify_method_response(response: str) -> TextContent:
    """Verify if a calculation is correct"""
    try:
        if("success" in response):
            print(f"[green] response {response} is verified")
            global is_correct 
            is_correct = "true"
        else:
            print(f"[red] response{response} is not matched")
       
        return TextContent(
            type="text",
            text=is_correct
        )
    except Exception as e:
        print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )
    
@mcp.tool()
async def draw_rectangle_in_paint(x1:int,y1:int,x2:int,y2:int) -> TextContent:
    """Open MS paint and Draw a rectangle using the coordinates from (x1,y1) to (x2,y2)"""
    # Step 1: Open MS Paintś
    try:
        #subprocess.Popen('mspaint')
        #time.sleep(3)
        # Check if MS Paint window is maximized
        
        window = pyautogui.getActiveWindow()
        # Activate MS Paint window
        window.activate()
        time.sleep(0.5)
        # check window size
        if window.isMaximized:
            print("MS Paint window is maximized")
            pyautogui.hotkey('win','down')
            time.sleep(0.5)
        else:
            print("MS Paint window is not maximized")

        # Step 3: Select Rectangle shape using keyboard
        pyautogui.press('alt')
        time.sleep(0.1)
        # pyautogui.press('h')
        # time.sleep(0.2)
        pyautogui.press('s')
        pyautogui.press('h')
        time.sleep(0.1)
        pyautogui.press('right', presses=4, interval=0.1)
        pyautogui.press('enter')
        time.sleep(0.5)
        print("-------rectangle selected---------")
        # step 3.5 intermediate step to maximum the paint screen
        pyautogui.hotkey('win', 'up')  # Maximize window
        # Step 4: Draw Rectangle
        pyautogui.moveTo(x1,y1, duration=1.5)
        pyautogui.mouseDown()
        pyautogui.moveTo(x2,y2, duration=1.5)
        pyautogui.mouseUp()
        time.sleep(0.5)

        #write_text(top_left[0],top_left[1],bottom_right[0],bottom_right[1])
        print(" Rectangle created in MS Paint.")
        return TextContent(
                    type="text",
                    text=f"Rectangle drawn from ({x1},{y1}) to ({x2},{y2})"
                )
    except Exception as e:
        return TextContent(
                    type="text",
                    text=f"Error drawing rectangle: {str(e)}"
                )
    
@mcp.tool()
def add_text_in_rectangle(x1:int,y1:int,x2:int,y2:int,text:str) -> TextContent:
    """write text inside the rectangle in opened ms paint"""
    # Step 5: Select Text Tool using keyboard
    try:
        window = pyautogui.getActiveWindow()

        if window is None:
            print("Could not find MS Paint window")
            return TextContent(
                        type="text",
                        text="Paint is not open. Please call open_paint first."
                    )
        if 'paint' not in window.title.lower():
            print("Active window does not contain 'paint' in title")
            return TextContent(
                        type="text", 
                        text="Paint is not open. Please call open_paint first."
                    )

        pyautogui.press('alt')
        time.sleep(0.2)
        pyautogui.press('t')
        time.sleep(0.2)
        pyautogui.press('x')  # T for Text
        time.sleep(0.5)

        # Make text bold
        # Step 7: Click inside the rectangle and write text
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        pyautogui.click()
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'b')
        time.sleep(0.2)
        pyautogui.write(text, interval=0.1)
    
        # Step 8: Exit text editing mode by clicking outside
        pyautogui.moveTo(center_x + 200, center_y + 200, duration=0.5)
        pyautogui.click()
        time.sleep(0.3)
        return TextContent(
                    type="text",
                    text=f"Text:'{text}' added successfully"
                )
    except Exception as e:
         return TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
@mcp.tool()
def fallback(error:dict) -> TextContent:
    """fallback(error_response: dict) - Any validation error will be catched and stop the execution."""
    return TextContent(
                    type="text",
                    text="Text: fallback is captured"
                )
@mcp.tool()
def internal_self_check(result: str) -> TextContent:
    """perform internal self check for every step before verify result"""
    if(result):
        return TextContent(
                    type="text",
                    text=f"Text: self {str} is verified"
                )

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print("CALLED: add(a: int, b: int) -> int:")
    return int(a + b)

@mcp.tool()
def calculate(expression: str) -> TextContent:
    """Calculate the result of an expression"""
    print("[blue]FUNCTION CALL:[/blue] calculate()")
    print(f"[blue]Expression:[/blue] {expression}")
    try:
        result = eval(expression)
        print(f"[green]Result:[/green] {result}")
        return TextContent(
            type="text",
            text=str(result)
        )
    except Exception as e:
        print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )
@mcp.tool()
async def open_paint() -> TextContent:
    """Open Microsoft Paint maximized on secondary monitor"""
    try:
        subprocess.Popen('mspaint')
        time.sleep(3)
        
        return TextContent(
                    type="text",
                    text="Paint opened successfully on secondary monitor and maximized"
                )
    except Exception as e:
        return TextContent(
                    type="text",
                    text=f"Error opening Paint: {str(e)}"
                )
    
@mcp.tool()
async def send_email(to_email: str, subject: str, body: str) -> TextContent:
    """Send an email using Gmail SMTP"""
    try:
        # Get Gmail credentials from environment variables
        gmail_email = os.getenv("SMTP_USERNAME")
        gmail_password = os.getenv("SMTP_PASSWORD")
        
        if not gmail_email or not gmail_password:
            error_msg = """Error: Gmail credentials not found. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD in your .env file.
                For Gmail, you need to create an App Password:
                1. Go to your Google Account settings
                2. Navigate to Security > 2-Step Verification
                3. At the bottom, select "App passwords"
                4. Create a new app password for "Mail" and "Windows Computer"
                5. Use this generated password as your GMAIL_APP_PASSWORD"""
            return TextContent(
                        type="text",
                        text=error_msg
                    )
                
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        # Login
        print("Logging in to Gmail account")
        try:
            server.login(gmail_email, gmail_password)
        except smtplib.SMTPAuthenticationError as auth_error:
            error_msg = f"""Error: Gmail authentication failed. Please check your credentials.
            
                        Error details: {str(auth_error)}

                        Make sure you're using an App Password, not your regular Gmail password.
                        For instructions on creating an App Password, see the README.md file."""
            
            print(f"error message {error_msg}")
            return {
                
                    TextContent(
                        type="text",
                        text=error_msg
                    )
                
            }
        
        # Send email
        print("Sending email")
        text = msg.as_string()
        #server.sendmail(gmail_email, to_email, text)
        
        # Close connection
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return TextContent(
                    type="text",
                    text=f"Email sent successfully to {to_email}"
                )
    except Exception as e:
        error_msg = f"""Error sending email: {str(e)}

If you're having trouble with Gmail authentication:
1. Make sure you're using an App Password, not your regular Gmail password
2. Check that your Gmail account has 2-Step Verification enabled
3. Verify that the email address in your .env file matches the one you created the App Password for"""
        
        print(error_msg)
        return TextContent(
                    type="text",
                    text=error_msg
                )    
if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution

# Example usage
#print(draw_rectangle_in_paint(780, 380,1140, 700))
#print(write_text_inside_rectangle(780, 380,1140, 700,"Automated string"))
