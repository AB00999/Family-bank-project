# Security Policy

## About Security in This Project

The Family Bank Project is an **educational/portfolio project** built for learning purposes. It demonstrates security best practices but is **NOT suitable for production use with real data**.

## Security Features Demonstrated

This project implements several security best practices:

### 1. Authentication & Password Security
- ✅ **Password Hashing**: Uses PBKDF2 with salted hashes (via Werkzeug)
- ✅ **No Plain Text Passwords**: Passwords are never stored as plain text
- ✅ **Secure Password Reset**: Single-use tokens with 30-minute expiration
- ✅ **Session Management**: HTTPOnly, SameSite, Secure cookies
- ✅ **Login Validation**: Timestamps and audit logging

### 2. Input Validation
- ✅ **CSRF Protection**: All forms protected with CSRF tokens
- ✅ **Form Validation**: Email format, username length, password strength
- ✅ **SQL Injection Prevention**: Parameterized queries with SQLite
- ✅ **Type Checking**: Input sanitization for all user inputs

### 3. HTTP Security Headers
- ✅ **X-Content-Type-Options**: nosniff
- ✅ **X-Frame-Options**: DENY (prevents clickjacking)
- ✅ **Referrer-Policy**: no-referrer
- ✅ **Cache-Control**: no-store (prevents caching sensitive data)

### 4. Database Security
- ✅ **Foreign Key Constraints**: Enabled to maintain data integrity
- ✅ **Transaction Management**: Proper rollback on errors
- ✅ **Backup Security**: Admin-only backup/restore with file validation
- ✅ **Data Encryption**: Password hashes not passwords
- ✅ **Audit Logging**: All security events are logged

### 5. Role-Based Access Control (RBAC)
- ✅ **User Roles**: Admin, Technician, User
- ✅ **Permission Checks**: Routes validate user role
- ✅ **Session Invalidation**: Password resets/changes invalidate sessions
- ✅ **Account Locking**: Admin can lock suspicious accounts
- ✅ **Audit Trail**: All role changes are logged

### 6. Application Security
- ✅ **Error Handling**: No sensitive info in error messages
- ✅ **Rate Limiting**: Consider adding for login attempts
- ✅ **Logging**: Security events are logged (account creation, sign-in, etc.)
- ✅ **Data Validation**: Input type checking on all endpoints

## Known Limitations

⚠️ This is a **learning project**. It has intentional limitations:

- **NOT PRODUCTION-READY**: Not suitable for real banking or personal data
- **Local Only**: Designed for local development, not public deployment
- **NO ENCRYPTION**: Sensitive data in transit is not encrypted (no HTTPS in dev)
- **DEMO ONLY**: All financial data and transactions are simulated
- **LIMITED RATE LIMITING**: No built-in rate limiting on endpoints
- **BASIC LOGGING**: Logging is in-memory and local file only
- **NO 2FA**: No two-factor authentication implemented

## Reporting Security Issues

If you find a security vulnerability in this educational project:

1. **DO NOT** create a public GitHub issue
2. **DO NOT** post details on social media
3. **DO** email the maintainer privately: [contact info would go here]
4. **DO** include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

The maintainer will:
- Acknowledge receipt within 48 hours
- Investigate and confirm the issue
- Develop a fix
- Issue a patched release
- Acknowledge your finding (unless you prefer anonymity)

## Security Best Practices for Users

If you use this project for learning:

### DO:
- ✅ Use ONLY made-up test data
- ✅ Never use real passwords or personal information
- ✅ Run locally only (127.0.0.1)
- ✅ Keep it on your personal computer
- ✅ Review the code before running
- ✅ Update dependencies regularly
- ✅ Read the security headers in app.py
- ✅ Study how authentication works

### DON'T:
- ❌ Deploy to public internet
- ❌ Use with real data
- ❌ Use real email addresses
- ❌ Use real passwords
- ❌ Share database backups publicly
- ❌ Modify security features without understanding them
- ❌ Commit secrets to Git
- ❌ Use in production

## Dependency Security

### Keeping Dependencies Updated

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt

# Create fresh requirements.txt
pip freeze > requirements.txt
```

### Dependencies Used
- **Flask**: Web framework
- **Werkzeug**: WSGI utilities (includes password hashing)
- **Python 3.8+**: Standard library only for core features

Dependabot is configured to check for updates weekly.

## Testing for Security

The project includes unit tests that verify:

```bash
python -m unittest discover -s tests -v
```

Tests cover:
- ✅ CSRF token validation
- ✅ Login with correct/incorrect passwords
- ✅ Protected routes (no access without auth)
- ✅ Role-based access control
- ✅ Duplicate bookings prevention
- ✅ Data validation on forms

## Compliance & Standards

This project demonstrates understanding of:

- **OWASP Top 10**: Addresses common vulnerabilities
- **PEP 249** (DB API): SQLite best practices
- **RFC 6749**: OAuth/security concepts
- **NIST Guidelines**: Password security, session management

## Security Audit Checklist

- [x] No hardcoded passwords or secrets
- [x] No sensitive data in logs
- [x] Password hashing implemented
- [x] CSRF protection on all forms
- [x] Input validation on all endpoints
- [x] SQL injection prevention
- [x] Session security headers set
- [x] Error handling without info leaks
- [x] Test coverage for security features
- [x] README documents security approach
- [ ] Rate limiting (future enhancement)
- [ ] Two-factor authentication (future enhancement)

## Learning Resources

To understand the security features implemented:

1. **Password Hashing**: Read about PBKDF2 and Werkzeug's implementation
2. **CSRF Protection**: Understand token generation and validation
3. **SQL Injection**: Learn parameterized queries
4. **Session Security**: Study HTTP cookie security flags
5. **RBAC**: Understand role-based access control

## Future Security Improvements

Planned enhancements:
- [ ] Add rate limiting on login attempts
- [ ] Implement two-factor authentication (2FA)
- [ ] Add HTTPS support
- [ ] Add logging to database instead of file
- [ ] Implement API rate limiting
- [ ] Add request signing for API endpoints
- [ ] Add password strength meter
- [ ] Implement account lockout after failed attempts

## Questions?

- Review the README.md for project overview
- Check CONTRIBUTING.md for development guidelines
- Explore the source code for implementation details
- Open an issue to discuss security concerns

---

**Last Updated**: November 2026  
**Maintainer**: Abdoul Sawadogo  
**Project Type**: Educational/Portfolio
