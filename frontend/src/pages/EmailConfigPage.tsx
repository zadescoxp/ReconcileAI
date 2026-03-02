import React, { useState, useEffect } from 'react';
import './EmailConfigPage.css';

interface EmailConfig {
    email: string;
    status: 'verified' | 'pending' | 'failed';
    verifiedAt?: string;
}

const EmailConfigPage: React.FC = () => {
    const [emails, setEmails] = useState<EmailConfig[]>([]);
    const [newEmail, setNewEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadEmailConfigs();
    }, []);

    const loadEmailConfigs = async () => {
        // TODO: Implement API call to fetch email configurations
        // For now, show placeholder data
        setEmails([
            {
                email: 'invoices@reconcileai.com',
                status: 'verified',
                verifiedAt: new Date().toISOString()
            }
        ]);
    };

    const validateEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleAddEmail = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);

        if (!validateEmail(newEmail)) {
            setError('Please enter a valid email address');
            return;
        }

        if (emails.some(e => e.email === newEmail)) {
            setError('This email address is already configured');
            return;
        }

        setLoading(true);
        try {
            // TODO: Implement API call to add email to SES
            // For now, simulate the action
            await new Promise(resolve => setTimeout(resolve, 1000));

            const newConfig: EmailConfig = {
                email: newEmail,
                status: 'pending',
            };

            setEmails([...emails, newConfig]);
            setNewEmail('');
            setSuccess(`Verification email sent to ${newEmail}. Please check your inbox and click the verification link.`);
        } catch (err) {
            setError('Failed to add email address. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveEmail = async (email: string) => {
        if (!window.confirm(`Are you sure you want to remove ${email}?`)) {
            return;
        }

        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            // TODO: Implement API call to remove email from SES
            await new Promise(resolve => setTimeout(resolve, 500));

            setEmails(emails.filter(e => e.email !== email));
            setSuccess(`Email address ${email} has been removed`);
        } catch (err) {
            setError('Failed to remove email address. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleResendVerification = async (email: string) => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            // TODO: Implement API call to resend verification
            await new Promise(resolve => setTimeout(resolve, 500));

            setSuccess(`Verification email resent to ${email}`);
        } catch (err) {
            setError('Failed to resend verification email. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'verified':
                return <span className="status-badge status-verified">✓ Verified</span>;
            case 'pending':
                return <span className="status-badge status-pending">⏳ Pending</span>;
            case 'failed':
                return <span className="status-badge status-failed">✗ Failed</span>;
            default:
                return <span className="status-badge">Unknown</span>;
        }
    };

    return (
        <div className="email-config-page">
            <div className="page-header">
                <h1>Email Configuration</h1>
                <p>Configure email addresses to receive invoices via Amazon SES</p>
            </div>

            {error && (
                <div className="alert alert-error">
                    <span className="alert-icon">⚠️</span>
                    <span>{error}</span>
                    <button className="alert-close" onClick={() => setError(null)}>×</button>
                </div>
            )}

            {success && (
                <div className="alert alert-success">
                    <span className="alert-icon">✓</span>
                    <span>{success}</span>
                    <button className="alert-close" onClick={() => setSuccess(null)}>×</button>
                </div>
            )}

            <div className="config-section">
                <h2>Add New Email Address</h2>
                <form onSubmit={handleAddEmail} className="add-email-form">
                    <div className="form-group">
                        <label htmlFor="email">Email Address</label>
                        <input
                            type="email"
                            id="email"
                            value={newEmail}
                            onChange={(e) => setNewEmail(e.target.value)}
                            placeholder="invoices@yourdomain.com"
                            disabled={loading}
                            required
                        />
                        <p className="form-help">
                            A verification email will be sent to this address. You must click the verification link before the email can receive invoices.
                        </p>
                    </div>
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Adding...' : 'Add Email Address'}
                    </button>
                </form>
            </div>

            <div className="config-section">
                <h2>Configured Email Addresses</h2>

                {emails.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">📧</div>
                        <h3>No Email Addresses Configured</h3>
                        <p>Add an email address above to start receiving invoices</p>
                    </div>
                ) : (
                    <div className="emails-table-container">
                        <table className="emails-table">
                            <thead>
                                <tr>
                                    <th>Email Address</th>
                                    <th>Status</th>
                                    <th>Verified At</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {emails.map((config) => (
                                    <tr key={config.email}>
                                        <td className="email-address">{config.email}</td>
                                        <td>{getStatusBadge(config.status)}</td>
                                        <td>
                                            {config.verifiedAt
                                                ? new Date(config.verifiedAt).toLocaleString()
                                                : '-'
                                            }
                                        </td>
                                        <td>
                                            <div className="action-buttons">
                                                {config.status === 'pending' && (
                                                    <button
                                                        className="btn-action btn-resend"
                                                        onClick={() => handleResendVerification(config.email)}
                                                        disabled={loading}
                                                    >
                                                        Resend Verification
                                                    </button>
                                                )}
                                                <button
                                                    className="btn-action btn-remove"
                                                    onClick={() => handleRemoveEmail(config.email)}
                                                    disabled={loading}
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="config-section info-section">
                <h2>📖 How It Works</h2>
                <div className="info-content">
                    <div className="info-step">
                        <div className="step-number">1</div>
                        <div className="step-content">
                            <h3>Add Email Address</h3>
                            <p>Enter the email address where you want to receive invoices</p>
                        </div>
                    </div>
                    <div className="info-step">
                        <div className="step-number">2</div>
                        <div className="step-content">
                            <h3>Verify Email</h3>
                            <p>Check your inbox and click the verification link from Amazon SES</p>
                        </div>
                    </div>
                    <div className="info-step">
                        <div className="step-number">3</div>
                        <div className="step-content">
                            <h3>Receive Invoices</h3>
                            <p>Once verified, invoices sent to this email will be automatically processed</p>
                        </div>
                    </div>
                    <div className="info-step">
                        <div className="step-number">4</div>
                        <div className="step-content">
                            <h3>Track Processing</h3>
                            <p>Monitor invoice processing status in the Invoices page</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="config-section warning-section">
                <h3>⚠️ Important Notes</h3>
                <ul>
                    <li>Email addresses must be verified before they can receive invoices</li>
                    <li>Verification links expire after 24 hours</li>
                    <li>Only PDF attachments will be processed from incoming emails</li>
                    <li>Processing typically takes 30-60 seconds per invoice</li>
                    <li>You'll be notified of any processing errors via the dashboard</li>
                </ul>
            </div>
        </div>
    );
};

export default EmailConfigPage;
