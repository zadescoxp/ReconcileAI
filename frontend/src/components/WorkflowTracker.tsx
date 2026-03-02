import React from 'react';
import { InvoiceStatus } from '../types/invoice';
import './WorkflowTracker.css';

interface WorkflowStep {
    id: string;
    label: string;
    status: 'completed' | 'active' | 'pending' | 'error';
    timestamp?: string;
    error?: string;
}

interface WorkflowTrackerProps {
    currentStatus: InvoiceStatus;
    receivedDate: string;
    error?: string;
}

const WorkflowTracker: React.FC<WorkflowTrackerProps> = ({
    currentStatus,
    receivedDate,
    error
}) => {

    const getWorkflowSteps = (): WorkflowStep[] => {
        const steps: WorkflowStep[] = [
            {
                id: 'received',
                label: 'Received',
                status: 'completed',
                timestamp: receivedDate
            },
            {
                id: 'extract',
                label: 'Extract Data',
                status: 'pending'
            },
            {
                id: 'match',
                label: 'AI Matching',
                status: 'pending'
            },
            {
                id: 'detect',
                label: 'Fraud Detection',
                status: 'pending'
            },
            {
                id: 'resolve',
                label: 'Resolution',
                status: 'pending'
            }
        ];

        // Update step statuses based on current invoice status
        switch (currentStatus) {
            case InvoiceStatus.RECEIVED:
                steps[0].status = 'completed';
                steps[1].status = 'active';
                break;

            case InvoiceStatus.EXTRACTING:
                steps[0].status = 'completed';
                steps[1].status = 'active';
                break;

            case InvoiceStatus.MATCHING:
                steps[0].status = 'completed';
                steps[1].status = 'completed';
                steps[2].status = 'active';
                break;

            case InvoiceStatus.DETECTING:
                steps[0].status = 'completed';
                steps[1].status = 'completed';
                steps[2].status = 'completed';
                steps[3].status = 'active';
                break;

            case InvoiceStatus.FLAGGED:
                steps[0].status = 'completed';
                steps[1].status = 'completed';
                steps[2].status = 'completed';
                steps[3].status = 'completed';
                steps[4].status = 'active';
                steps[4].label = 'Awaiting Approval';
                break;

            case InvoiceStatus.APPROVED:
                steps.forEach(step => step.status = 'completed');
                steps[4].label = 'Approved';
                break;

            case InvoiceStatus.REJECTED:
                steps.forEach(step => step.status = 'completed');
                steps[4].label = 'Rejected';
                steps[4].status = 'error';
                break;
        }

        // If there's an error, mark the current active step as error
        if (error) {
            const activeStep = steps.find(s => s.status === 'active');
            if (activeStep) {
                activeStep.status = 'error';
                activeStep.error = error;
            }
        }

        return steps;
    };

    const steps = getWorkflowSteps();

    const getStepIcon = (status: string): string => {
        switch (status) {
            case 'completed':
                return '✓';
            case 'active':
                return '⟳';
            case 'error':
                return '✗';
            default:
                return '○';
        }
    };

    const formatTimestamp = (timestamp?: string): string => {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatusMessage = (): string => {
        switch (currentStatus) {
            case InvoiceStatus.RECEIVED:
                return 'Invoice received and queued for processing';
            case InvoiceStatus.EXTRACTING:
                return 'Extracting text and data from PDF...';
            case InvoiceStatus.MATCHING:
                return 'AI is matching invoice against purchase orders...';
            case InvoiceStatus.DETECTING:
                return 'Running fraud detection checks...';
            case InvoiceStatus.FLAGGED:
                return 'Invoice flagged for human review';
            case InvoiceStatus.APPROVED:
                return 'Invoice approved and ready for payment';
            case InvoiceStatus.REJECTED:
                return 'Invoice rejected';
            default:
                return 'Processing...';
        }
    };

    const isProcessing = [
        InvoiceStatus.RECEIVED,
        InvoiceStatus.EXTRACTING,
        InvoiceStatus.MATCHING,
        InvoiceStatus.DETECTING
    ].includes(currentStatus);

    return (
        <div className="workflow-tracker">
            <div className="workflow-header">
                <h3>Processing Status</h3>
                <div className={`status-message ${isProcessing ? 'processing' : ''}`}>
                    {isProcessing && <span className="spinner">⟳</span>}
                    {getStatusMessage()}
                </div>
            </div>

            <div className="workflow-steps">
                {steps.map((step, index) => (
                    <React.Fragment key={step.id}>
                        <div className={`workflow-step ${step.status}`}>
                            <div className="step-indicator">
                                <div className="step-icon">{getStepIcon(step.status)}</div>
                                {step.status === 'active' && (
                                    <div className="step-pulse"></div>
                                )}
                            </div>
                            <div className="step-content">
                                <div className="step-label">{step.label}</div>
                                {step.timestamp && (
                                    <div className="step-timestamp">
                                        {formatTimestamp(step.timestamp)}
                                    </div>
                                )}
                                {step.error && (
                                    <div className="step-error">{step.error}</div>
                                )}
                            </div>
                        </div>

                        {index < steps.length - 1 && (
                            <div className={`workflow-connector ${steps[index + 1].status === 'completed' ? 'completed' : ''
                                }`}>
                                <div className="connector-line"></div>
                            </div>
                        )}
                    </React.Fragment>
                ))}
            </div>

            {isProcessing && (
                <div className="workflow-footer">
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{
                                width: `${((steps.filter(s => s.status === 'completed').length) / steps.length) * 100}%`
                            }}
                        ></div>
                    </div>
                    <div className="progress-text">
                        {steps.filter(s => s.status === 'completed').length} of {steps.length} steps completed
                    </div>
                </div>
            )}

            {currentStatus === InvoiceStatus.FLAGGED && (
                <div className="workflow-alert workflow-alert-warning">
                    <span className="alert-icon">⚠️</span>
                    <span>This invoice requires human approval before proceeding</span>
                </div>
            )}

            {currentStatus === InvoiceStatus.APPROVED && (
                <div className="workflow-alert workflow-alert-success">
                    <span className="alert-icon">✓</span>
                    <span>Invoice approved and ready for payment processing</span>
                </div>
            )}

            {currentStatus === InvoiceStatus.REJECTED && (
                <div className="workflow-alert workflow-alert-error">
                    <span className="alert-icon">✗</span>
                    <span>Invoice rejected and will not be processed</span>
                </div>
            )}
        </div>
    );
};

export default WorkflowTracker;
