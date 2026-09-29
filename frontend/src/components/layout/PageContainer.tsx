import type { ReactNode } from "react";

interface PageContainerProps {
	children: ReactNode;
}

function PageContainer({
	children,
}: PageContainerProps) {
	return (
		<main className="page-content">
			<div className="page-container">
				{children}
			</div>
		</main>
	);
}

export default PageContainer;
