"use client";

import { useState } from "react";

interface Step {
  title: string;
  description: string;
}

interface WorkflowAccordionProps {
  steps: Step[];
}

export default function WorkflowAccordion({ steps }: WorkflowAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <div className="landing-accordion">
      {steps.map((step, index) => {
        const isOpen = openIndex === index;
        return (
          <div key={step.title} className="landing-accordion__item">
            <button
              type="button"
              className={`landing-accordion__trigger ${isOpen ? "landing-accordion__trigger--open" : ""}`}
              onClick={() => setOpenIndex(isOpen ? null : index)}
              aria-expanded={isOpen}
              data-cursor-hover
            >
              <span>{step.title}</span>
              <span className="landing-accordion__icon">{isOpen ? "−" : "+"}</span>
            </button>
            <div
              className="landing-accordion__panel"
              style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
            >
              <div className="landing-accordion__panel-inner">
                <p>{step.description}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
