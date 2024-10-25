CREATE DATABASE rent_crawler;

USE rent_crawler;

CREATE TABLE rent_ads (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    price INT,
    safetyDeposit INT,
    agencyRentalFee INT,
    surfaceArea INT,
    roomsQuantity INT,
    energyClassification VARCHAR(2),
    thumbnailUrl VARCHAR(255),
    url VARCHAR(255)
);