CREATE TABLE Caregivers (
    Username varchar(255),
    Salt BINARY(16),
    Hash BINARY(16),
    PRIMARY KEY (Username)
);

CREATE TABLE Vaccines (
    Name varchar(255),
    Doses int,
    PRIMARY KEY (Name)
);

CREATE TABLE Availabilities (
    Time date,
    Username varchar(255),
    apptID varchar(255),
    Name varchar(255),
    PRIMARY KEY (Time, Username),
    FOREIGN KEY (Name) REFERENCES Vaccines,
    FOREIGN KEY (Username) REFERENCES Caregivers
);

CREATE TABLE Patients (
	Username varchar(255) PRIMARY KEY,
	Salt BINARY(16),
	Hash BINARY(16),
	apptID varchar(255),
);