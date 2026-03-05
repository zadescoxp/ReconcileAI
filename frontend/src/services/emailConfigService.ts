import { fetchAuthSession } from 'aws-amplify/auth';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT;

interface EmailConfig {
    email: string;
    status: 'verified' | 'pending' | 'failed';
    verifiedAt?: string;
}

interface ApiResponse<T> {
    data?: T;
    error?: string;
}

async function getAuthHeaders(): Promise<HeadersInit> {
    try {
        const session = await fetchAuthSession();
        const token = session.tokens?.idToken?.toString();

        return {
            'Content-Type': 'application/json',
            'Authorization': token || '',
        };
    } catch (error) {
        console.error('Error getting auth headers:', error);
        throw new Error('Authentication required');
    }
}

export const EmailConfigService = {
    /**
     * List all configured email addresses
     */
    async listEmails(): Promise<ApiResponse<EmailConfig[]>> {
        try {
            const headers = await getAuthHeaders();
            const response = await fetch(`${API_ENDPOINT}email-config`, {
                method: 'GET',
                headers,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to fetch emails');
            }

            const data = await response.json();
            return { data: data.emails || [] };
        } catch (error) {
            console.error('Error listing emails:', error);
            return { error: error instanceof Error ? error.message : 'Unknown error' };
        }
    },

    /**
     * Add a new email address for verification
     */
    async addEmail(email: string): Promise<ApiResponse<{ message: string; email: string; status: string }>> {
        try {
            const headers = await getAuthHeaders();
            const response = await fetch(`${API_ENDPOINT}email-config`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to add email');
            }

            const data = await response.json();
            return { data };
        } catch (error) {
            console.error('Error adding email:', error);
            return { error: error instanceof Error ? error.message : 'Unknown error' };
        }
    },

    /**
     * Remove an email address
     */
    async removeEmail(email: string): Promise<ApiResponse<{ message: string }>> {
        try {
            const headers = await getAuthHeaders();
            const response = await fetch(`${API_ENDPOINT}email-config`, {
                method: 'DELETE',
                headers,
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to remove email');
            }

            const data = await response.json();
            return { data };
        } catch (error) {
            console.error('Error removing email:', error);
            return { error: error instanceof Error ? error.message : 'Unknown error' };
        }
    },

    /**
     * Resend verification email
     */
    async resendVerification(email: string): Promise<ApiResponse<{ message: string }>> {
        try {
            const headers = await getAuthHeaders();
            const response = await fetch(`${API_ENDPOINT}email-config/resend`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to resend verification');
            }

            const data = await response.json();
            return { data };
        } catch (error) {
            console.error('Error resending verification:', error);
            return { error: error instanceof Error ? error.message : 'Unknown error' };
        }
    },
};
