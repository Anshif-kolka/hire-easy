"""
Email Ingest Agent - Automatically fetch and process resumes from email.
"""
import imaplib
import email
from email.header import decode_header
import re
import os
import tempfile
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EmailAttachment:
    """Represents an email attachment."""
    filename: str
    content: bytes
    content_type: str


@dataclass
class ProcessedEmail:
    """Represents a processed email."""
    message_id: str
    subject: str
    sender: str
    job_title: Optional[str]
    attachments: List[EmailAttachment]
    received_at: datetime


class EmailIngestAgent:
    """
    Agent that monitors an email inbox for job applications and extracts resumes.
    
    Expected email subject format: "JOB - {Job Title} - APPLICATION"
    """
    
    def __init__(
        self,
        imap_server: str,
        email_address: Optional[str],
        email_password: Optional[str],
        folder: str = "INBOX",
        subject_pattern: str = r"^JOB\s*-\s*(.+?)\s*-\s*APPLICATION$"
    ):
        """
        Initialize Email Ingest Agent.
        
        Args:
            imap_server: IMAP server address (e.g., imap.gmail.com)
            email_address: Email address to monitor
            email_password: Email password or app password
            folder: Email folder to monitor
            subject_pattern: Regex pattern to match job application emails
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.email_password = email_password
        self.folder = folder
        self.subject_pattern = re.compile(subject_pattern, re.IGNORECASE)
        
        self._connection = None
    
    def is_configured(self) -> bool:
        """Check if email ingestion is properly configured."""
        return bool(self.email_address and self.email_password)
    
    def connect(self) -> bool:
        """
        Connect to the IMAP server.
        
        Returns:
            True if connection successful
        """
        if not self.is_configured():
            logger.warning("Email ingestion not configured")
            return False
        
        try:
            self._connection = imaplib.IMAP4_SSL(self.imap_server)
            self._connection.login(self.email_address, self.email_password)
            self._connection.select(self.folder)
            logger.info(f"Connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to email: {e}")
            self._connection = None
            return False
    
    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self._connection:
            try:
                self._connection.logout()
            except:
                pass
            self._connection = None
    
    def fetch_unread_applications(self) -> List[ProcessedEmail]:
        """
        Fetch unread job application emails.
        
        Returns:
            List of ProcessedEmail objects
        """
        if not self._connection:
            if not self.connect():
                return []
        
        try:
            # Search for unread emails
            status, messages = self._connection.search(None, 'UNSEEN')
            if status != 'OK':
                logger.warning("Failed to search emails")
                return []
            
            email_ids = messages[0].split()
            processed_emails = []
            
            for email_id in email_ids:
                processed = self._process_email(email_id)
                if processed:
                    processed_emails.append(processed)
            
            logger.info(f"Found {len(processed_emails)} job application emails")
            return processed_emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _process_email(self, email_id: bytes) -> Optional[ProcessedEmail]:
        """
        Process a single email.
        
        Args:
            email_id: Email ID from IMAP
            
        Returns:
            ProcessedEmail or None if not a job application
        """
        try:
            status, msg_data = self._connection.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get message ID
            message_id = msg.get('Message-ID', str(email_id))
            
            # Decode subject
            subject = self._decode_header(msg['Subject'])
            
            # Check if subject matches our pattern
            match = self.subject_pattern.match(subject.strip())
            if not match:
                logger.debug(f"Email '{subject}' doesn't match application pattern")
                return None
            
            job_title = match.group(1).strip()
            
            # Get sender
            sender = self._decode_header(msg['From'])
            
            # Get date
            date_str = msg.get('Date', '')
            try:
                received_at = email.utils.parsedate_to_datetime(date_str)
            except:
                received_at = datetime.utcnow()
            
            # Extract PDF attachments
            attachments = self._extract_attachments(msg)
            
            if not attachments:
                logger.warning(f"No PDF attachments in email from {sender}")
                return None
            
            return ProcessedEmail(
                message_id=message_id,
                subject=subject,
                sender=sender,
                job_title=job_title,
                attachments=attachments,
                received_at=received_at
            )
            
        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8'))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(part)
        
        return ''.join(result)
    
    def _extract_attachments(self, msg: email.message.Message) -> List[EmailAttachment]:
        """
        Extract PDF attachments from email.
        
        Args:
            msg: Email message
            
        Returns:
            List of EmailAttachment objects
        """
        attachments = []
        
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            
            # Check for PDF attachment
            if 'attachment' in content_disposition or content_type == 'application/pdf':
                filename = part.get_filename()
                
                if filename:
                    filename = self._decode_header(filename)
                    
                    # Only process PDF files
                    if filename.lower().endswith('.pdf'):
                        content = part.get_payload(decode=True)
                        
                        if content:
                            attachments.append(EmailAttachment(
                                filename=filename,
                                content=content,
                                content_type=content_type
                            ))
        
        return attachments
    
    def save_attachment_temp(self, attachment: EmailAttachment) -> str:
        """
        Save attachment to a temporary file.
        
        Args:
            attachment: EmailAttachment object
            
        Returns:
            Path to temporary file
        """
        fd, path = tempfile.mkstemp(suffix='.pdf')
        try:
            os.write(fd, attachment.content)
        finally:
            os.close(fd)
        
        return path
    
    def mark_as_read(self, message_id: str):
        """
        Mark an email as read.
        
        Args:
            message_id: Email message ID
        """
        # This is handled automatically by IMAP when we fetch with UNSEEN
        pass
    
    def poll_and_process(self, callback) -> int:
        """
        Poll for new emails and process them with a callback.
        
        Args:
            callback: Function to call for each (job_title, pdf_bytes) pair
            
        Returns:
            Number of resumes processed
        """
        if not self.is_configured():
            logger.info("Email ingestion not configured, skipping poll")
            return 0
        
        emails = self.fetch_unread_applications()
        processed_count = 0
        
        for email_data in emails:
            for attachment in email_data.attachments:
                try:
                    callback(
                        job_title=email_data.job_title,
                        pdf_bytes=attachment.content,
                        filename=attachment.filename,
                        sender=email_data.sender,
                        message_id=email_data.message_id
                    )
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment.filename}: {e}")
        
        self.disconnect()
        return processed_count
