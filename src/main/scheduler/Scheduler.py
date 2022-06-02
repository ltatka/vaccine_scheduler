from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime
import re


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def create_patient(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_patient(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    patient = Patient(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        patient.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)

def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False

def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_patient
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
        current_patient = patient
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if patient is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_patient = patient

def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):

    global current_caregiver
    global current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first!")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    # Check for arguments
    if len(tokens) !=2:
        print("Please provide a date (MM-DD-YYYY) to search for availability.")
        return
    # Process and format date token
    date = tokens[1]

    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")

    try:
        month = int(date_tokens[0])
        day = int(date_tokens[1])
        year = int(date_tokens[2])
        d = datetime.datetime(year, month, day)
    except:
        print("Please enter the date in the form MM-DD-YYYY")
        return

    # Get vaccine inventory and check that there are doses available
    inventory = get_vaccine_inventory()
    if not inventory:
        print("There are no vaccines available at this time. Try again later.")
        return

    try:
        get_caregiver_schedule = "SELECT Username, Time FROM Availabilities WHERE Time = %s AND apptID IS NULL " \
                                 "ORDER BY Username;"
        cursor.execute(get_caregiver_schedule, d)
        if cursor.rowcount == 0:
            print(f"There are no appointments available on {month}-{day}-{year}\n"
                  f"Try another date.")
            return
        print("PROVIDERS:")
        for row in cursor:
            print(row['Username'])
        print("\nVACCINE AVAILABILITY:")
        for key in inventory:
            print(f"{key} {inventory[key]}")
    except pymssql.Error as e:
         raise e
    finally:
        cm.close_connection()
    return None

def get_vaccine_inventory(name=None):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    query = "SELECT SUM(Doses) as total FROM Vaccines;"
    cursor.execute(query)
    total = None
    for row in cursor:
        total = row['total']
    if total == 0:
        return None
    if name:
        query = "SELECT Name, Doses FROM Vaccines WHERE Name=%s"
        cursor.execute(query, name)
    else:
        query = "SELECT Name, Doses FROM Vaccines ORDER BY Doses;"
        cursor.execute(query)

    inventory = {}
    for row in cursor:
        inventory[row['Name']] = row['Doses']
    cm.close_connection()
    return inventory


def reserve(tokens):
    """
    """
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_patient
    global current_caregiver
    if current_caregiver:
        print("You must be a patient to reserve an appointment.")
        return
    if not current_patient:
        print("Please login to reserve an appointment")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Invalid input.\nMust enter 'reserve <date> <vaccine name>'")
        return

    date = tokens[1]
    vaccine_name = tokens[2]

    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    d = datetime.datetime(year, month, day)

    # Get vaccine inventory and check that there are doses available
    if not is_vaccine_name_valid(vaccine_name):
        print("Invalid vaccine name, try again.")
        return
    inventory = get_vaccine_inventory(name=vaccine_name)
    if not inventory:
        print(f"There are no {vaccine_name} vaccines available at this time. Try again later or select a different "
              f"vaccine.")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    try:
        check_appt = "SELECT COUNT(apptID) as total FROM Patients WHERE Username=%s;"
        cursor.execute(check_appt, current_patient.get_username())
        for row in cursor:
            if row['total'] > 0:
                print("You already have an appointment.\n"
                      "To show exisiting appointments: show_appointments\n"
                      "To cancel an appointment: cancel <appointmentID>")
                return

        get_caregiver_schedule = "SELECT TOP 1 Username, apptID FROM Availabilities " \
                                 "WHERE Time = %s AND apptID IS NULL ORDER BY Username;"
        cursor.execute(get_caregiver_schedule, d)
        if cursor.rowcount == 0:
            print(f"There are no appointments available on {month}-{day}-{year}\n"
                  f"Try another date.")
            return
        for row in cursor:
            caregiver = row['Username']
        apptID = Util.generate_apptID()
        upload_reservation(caregiver, d, apptID, vaccine_name)
        increment_doses(vaccine_name)
        print(f"Appointment ID: {apptID}, Caregiver username: {caregiver}")
    except Exception as e:
        print(e)
        print("An error occurred. No reservation was made.")
        return
    finally:
        cm.close_connection()


def upload_reservation(caregiver, d, apptID, vaccine_name):
    global current_patient

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    patient_name = current_patient.get_username()
    add_apptID = "UPDATE Patients SET apptID=%s WHERE Username = %s;"
    update_availability = "UPDATE Availabilities SET Name=%s, apptID=%s WHERE " \
                          "Time=%s AND Username=%s;"
    try:
        cursor.execute(add_apptID, (apptID, patient_name))
        cursor.execute(update_availability, (vaccine_name, apptID, d, caregiver))
        conn.commit()
    except pymssql.Error:
        raise
    finally:
        cm.close_connection()

def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def cancel(tokens):
    global current_patient
    global current_caregiver
    if current_patient is None and current_caregiver is None:
        print("Please login first.")
        return
    if len(tokens) != 2:
        print("Please enter the appointment ID to cancel your appointment.")
    apptID = tokens[1]
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    if not appt_reserved(apptID):
        print("There is no appointment with this appointment ID.\n"
              "Please ensure appointment ID is correct.\n"
              "To show an existing appointment and ID, use 'show_appointments'")
        return
    try:
        get_vaccine_name = "SELECT Name FROM Availabilities WHERE apptID=%s;"
        cursor.execute(get_vaccine_name, apptID)
        for row in cursor:
            vaccine_name = row['Name']
        if current_patient: # For patients: make the appointment available again
            cancel_appt = "UPDATE Availabilities SET apptID=NULL, Name=NULL WHERE apptID=%s;"
            cursor.execute(cancel_appt, apptID)
            patient = current_patient.get_username()
        else: # For caregivers: remove the time slot from availability
            get_pt_name = "SELECT p.Username Patient FROM Availabilities a JOIN Patients p ON a.apptID=p.apptID " \
                          "WHERE a.apptID=%s;"
            cursor.execute(get_pt_name, apptID)
            for row in cursor:
                patient = row['Patient']
            remove_time_slot = "DELETE FROM Availabilities WHERE apptID=%s"
            cursor.execute(remove_time_slot, apptID)
        delete_apptID = "UPDATE Patients SET apptID = NULL WHERE Username=%s;"
        cursor.execute(delete_apptID, patient)

        # Add vaccine dose back to inventory
        increment_doses(vaccine_name, decrease=False)
        conn.commit()
        print(f"Appointment successfully cancelled.")
        cm.close_connection()
    except:
        print(f"An error occurred. Appointment {apptID} was not cancelled. Try again.")
        return

def appt_reserved(apptID):
    global current_caregiver
    global current_patient

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        if current_caregiver:
            get_appointment = "SELECT * FROM Availabilities WHERE apptID=%s AND Username=%s;"
            user = current_caregiver.get_username()
        else:
            get_appointment = "SELECT * FROM Availabilities a JOIN Patients p " \
                              "ON a.apptID = p.apptID WHERE a.apptID=%s AND p.Username=%s;"
            user = current_patient.get_username()
        cursor.execute(get_appointment, (apptID, user))
        return cursor.rowcount != 0
    except Exception as e:
        print(e)
        print("An error occurred.")
        return
    finally:
        cm.close_connection()


def increment_doses(vaccine_name, decrease=True):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        if decrease:
            change_doses = "UPDATE Vaccines SET Doses = Doses - 1 WHERE Name=%s AND Doses>0;"
        else:
            change_doses = "UPDATE Vaccines SET Doses = Doses + 1 WHERE Name=%s;"
        cursor.execute(change_doses, vaccine_name)
        conn.commit()
    except pymssql.Error as e:
        print("Error occurred when incrementing doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when incrementing doses")
        print("Error:", e)
        return
    finally:
        cm.close_connection()

def is_vaccine_name_valid(vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        statement = "SELECT COUNT(*) AS total FROM Vaccines WHERE Name=%s;"
        cursor.execute(statement, vaccine_name)
        isValid = False
        for row in cursor:
            isValid = row['total'] != 0
        cm.close_connection()
        return isValid
    except Exception:
        print("An error occurred.")

def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    try:
        doses = int(tokens[2])
    except:
        print("Error occurred when adding doses")
        return
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def show_appointments(tokens):
    global current_patient
    global current_caregiver
    if current_caregiver is None and current_patient is None:
        print("Please login first!")
        return
    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)

        if current_caregiver:
            get_appointments = "SELECT a.apptID, Name, Time, Username " \
                               "FROM (SELECT apptID, Time, Name FROM Availabilities WHERE Username=%s) a " \
                               "JOIN Patients p ON p.apptID = a.apptID ORDER BY a.apptID"

            cursor.execute(get_appointments, current_caregiver.get_username())
        else:
            get_appointments = "SELECT a.apptID, Name, Time, a.Username "\
                               "FROM (SELECT Username, apptID from Patients) p JOIN " \
                               "(SELECT apptID, Name, Time, Username FROM Availabilities) a " \
                               "ON p.apptID = a.apptID " \
                               "WHERE p.Username = %s"
            cursor.execute(get_appointments, current_patient.get_username())
        if cursor.rowcount == 0:
            print("There are no appointments scheduled.")
            return
        for row in cursor:
            print(f"{row['apptID']} {row['Name']} {row['Time'].month}-{row['Time'].day}-{row['Time'].year} "
                  f"{row['Username']}")
    except Exception as e:
        print(e)
        print("Please try again!")



def logout(tokens):
    global current_patient
    global current_caregiver
    try:
        if current_patient is None and current_caregiver is None:
            print("Please login first.")
            return
        current_patient = None
        current_caregiver = None
        print("Successfully logged out!")
        return
    except Exception:
        print("Please try again!")
        return



def start():
    stop = False
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")  # // TODO: implement login_patient (Part 1)
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")  # // TODO: implement search_caregiver_schedule (Part 2)
    print("> reserve <date> <vaccine>")  # // TODO: implement reserve (Part 2)
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")  # // TODO: implement cancel (extra credit)
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")  # // TODO: implement show_appointments (Part 2)
    print("> logout")  # // TODO: implement logout (Part 2)
    print("> Quit")
    print()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == cancel:
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "cancel":
            cancel(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        else:
            print("Invalid operation name!")



if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
