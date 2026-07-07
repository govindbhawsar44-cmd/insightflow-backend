#!/usr/bin/env bash

# Ensure uploads directory exists
mkdir -p uploads

# Recreate schema.prisma because the persistent disk mount hides the original file
cat << 'EOF' > prisma/schema.prisma
generator client {
  provider = "prisma-client-py"
}

datasource db {
  provider = "sqlite"
  url      = "file:./dev.db"
}

model User {
  id            String    @id @default(uuid())
  email         String    @unique
  name          String?
  passwordHash  String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  datasets      Dataset[]
  chats         Chat[]
  reports       Report[]
}

model Dataset {
  id              String     @id @default(uuid())
  name            String
  size            Int
  url             String
  originalUrl     String?
  cleaningHistory String?
  qualityScore    Int?
  userId          String
  user            User       @relation(fields: [userId], references: [id])
  dashboard       Dashboard?
  reports         Report[]
  createdAt       DateTime   @default(now())
  updatedAt       DateTime   @updatedAt
}

model Dashboard {
  id          String   @id @default(uuid())
  datasetId   String   @unique
  dataset     Dataset  @relation(fields: [datasetId], references: [id])
  layout      String
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Chat {
  id          String    @id @default(uuid())
  title       String
  userId      String
  user        User      @relation(fields: [userId], references: [id])
  messages    Message[]
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
}

model Message {
  id        String   @id @default(uuid())
  chatId    String
  chat      Chat     @relation(fields: [chatId], references: [id])
  role      String   // "user" or "assistant"
  content   String
  createdAt DateTime @default(now())
}

model Report {
  id        String   @id @default(uuid())
  title     String
  type      String   @default("Business Analysis")
  datasetId String?
  dataset   Dataset? @relation(fields: [datasetId], references: [id])
  content   String
  userId    String
  user      User     @relation(fields: [userId], references: [id])
  createdAt DateTime @default(now())
}
EOF

# Generate the client and Push DB schema to create dev.db if it doesn't exist at runtime
python -m prisma generate
python -m prisma db push --accept-data-loss

# Start the Uvicorn server, binding to the port provided by the host environment
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
