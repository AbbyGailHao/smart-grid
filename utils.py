import os

def clear_screen():
    """Clears the terminal screen securely across Windows, Mac, and Linux."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a standardized, professional ASCII header."""
    clear_screen()
    print("=" * 70)
    print(f" {title} ".center(70, "="))
    print("=" * 70)

def pause():
    """Pauses execution until the user presses Enter, catching keyboard interrupts safely."""
    try:
        input("\nPress Enter to continue...")
    except (KeyboardInterrupt, EOFError):
        print("\n[Operation interrupted. Returning to menu...]")
        
OUTPUT_DIR = "reports_output"

def ensure_output_dir():
    """Ensures the designated output reports directory exists."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    return OUTPUT_DIR
def get_secure_choice(prompt, min_val, max_val):
    """
    Bulletproof input validator. Prevents ValueErrors, infinite loops, 
    and out-of-bounds inputs during live CLI execution.
    """
    while True:
        try:
            choice = input(prompt).strip()
            if not choice:
                print("[ERROR] Input cannot be empty. Please try again.")
                continue
            val = int(choice)
            if min_val <= val <= max_val:
                return val
            print(f"[ERROR] Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("[ERROR] Invalid input. Please enter a valid numeric value.")