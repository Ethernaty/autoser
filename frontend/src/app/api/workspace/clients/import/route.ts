import { NextRequest } from "next/server";
import { directoryProxy } from "@/features/workspace/api/directory-proxy";
export async function POST(request: NextRequest) { return directoryProxy(request, "/clients/import", ["clients.create"]); }
