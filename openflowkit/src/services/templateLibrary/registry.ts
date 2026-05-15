import type { FlowEdge, FlowNode } from '@/lib/types';
import type { TemplateManifest } from './types';

export interface TemplateRegistry {
    getTemplate(templateId: string): TemplateManifest | undefined;
    listTemplates(): TemplateManifest[];
    registerTemplate(template: TemplateManifest): void;
}

function cloneNodes(nodes: FlowNode[]): FlowNode[] {
    return nodes.map((node) => ({
        ...node,
        position: { ...node.position },
        data: { ...node.data },
        style: node.style ? { ...node.style } : undefined,
    }));
}

function cloneEdges(edges: FlowEdge[]): FlowEdge[] {
    return edges.map((edge) => ({
        ...edge,
        data: edge.data ? { ...edge.data } : undefined,
        style: edge.style ? { ...edge.style } : undefined,
        markerStart: edge.markerStart,
        markerEnd: edge.markerEnd,
    }));
}

function cloneTemplate(template: TemplateManifest): TemplateManifest {
    return {
        ...template,
        tags: [...template.tags],
        graph: {
            nodes: cloneNodes(template.graph.nodes),
            edges: cloneEdges(template.graph.edges),
        },
    };
}

export function createTemplateRegistry(initialTemplates: TemplateManifest[] = []): TemplateRegistry {
    const templatesById = new Map<string, TemplateManifest>();

    function registerTemplate(template: TemplateManifest): void {
        if (templatesById.has(template.id)) {
            throw new Error(`Template already registered: ${template.id}`);
        }
        templatesById.set(template.id, cloneTemplate(template));
    }

    for (const template of initialTemplates) {
        registerTemplate(template);
    }

    return {
        getTemplate(templateId: string): TemplateManifest | undefined {
            const template = templatesById.get(templateId);
            return template ? cloneTemplate(template) : undefined;
        },
        listTemplates(): TemplateManifest[] {
            return Array.from(templatesById.values()).map(cloneTemplate);
        },
        registerTemplate,
    };
}
