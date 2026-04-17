
import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";

const http = httpRouter();

http.route({
  path: "/api/getUserByEmail",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { email } = await request.json();
    const user = await ctx.runQuery(internal.api.getUserByEmail, { email });
    return new Response(JSON.stringify(user), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getUserById",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { id } = await request.json();
    const user = await ctx.runQuery(internal.api.getUserById, { id });
    return new Response(JSON.stringify(user), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/registerOrganizer",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { email, passwordHash, name } = await request.json();
    try {
      const userId = await ctx.runMutation(internal.api.registerOrganizer, {
        email,
        passwordHash,
        name,
      });
      return new Response(JSON.stringify({ success: true, userId }), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (error: any) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

http.route({
  path: "/api/loginUser",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { email, password } = await request.json();
    const user = await ctx.runQuery(internal.api.loginUser, { email, password });
    return new Response(JSON.stringify(user || null), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getEventsByOrganizer",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { organizerId } = await request.json();
    const events = await ctx.runQuery(internal.api.getEventsByOrganizer, { organizerId });
    return new Response(JSON.stringify(events), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getEventById",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { id } = await request.json();
    const event = await ctx.runQuery(internal.api.getEventById, { id });
    return new Response(JSON.stringify(event), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getEventPaymentStatus",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId } = await request.json();
    const status = await ctx.runQuery(internal.api.getEventPaymentStatus, { eventId });
    return new Response(JSON.stringify(status), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/updateEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { id, name, startDate, endDate, description } = await request.json();
    const eventId = await ctx.runMutation(internal.api.updateEvent, {
      id,
      name,
      startDate,
      endDate,
      description,
    });
    return new Response(JSON.stringify({ eventId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/deleteEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { id } = await request.json();
    await ctx.runMutation(internal.api.deleteEvent, { id });
    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/createEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { organizerId, name, startDate, endDate, description, plan } = await request.json();
    const args: any = { organizerId, name };
    if (startDate !== null && startDate !== undefined) args.startDate = startDate;
    if (endDate !== null && endDate !== undefined) args.endDate = endDate;
    if (description !== null && description !== undefined && description !== "") args.description = description;
    if (plan !== null && plan !== undefined) args.plan = plan;
    const eventId = await ctx.runMutation(internal.api.createEvent, args);
    return new Response(JSON.stringify({ eventId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getCommitteesByEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId } = await request.json();
    const committees = await ctx.runQuery(internal.api.getCommitteesByEvent, { eventId });
    return new Response(JSON.stringify(committees), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/createCommittee",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, name, agenda, chair, coChair } = await request.json();
    const args: any = { eventId, name };
    if (agenda !== null && agenda !== undefined && agenda !== "") args.agenda = agenda;
    if (chair !== null && chair !== undefined && chair !== "") args.chair = chair;
    if (coChair !== null && coChair !== undefined && coChair !== "") args.coChair = coChair;
    const committeeId = await ctx.runMutation(internal.api.createCommittee, args);
    return new Response(JSON.stringify({ committeeId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getDelegatesByEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId } = await request.json();
    const delegates = await ctx.runQuery(internal.api.getDelegatesByEvent, { eventId });
    return new Response(JSON.stringify(delegates), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getAllDelegates",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const delegates = await ctx.runQuery(internal.api.getAllDelegates);
    return new Response(JSON.stringify(delegates), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/createDelegate",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { email, passwordHash, name, country } = await request.json();
    const userId = await ctx.runMutation(internal.api.createDelegate, {
      email,
      passwordHash,
      name,
      country,
    });
    return new Response(JSON.stringify({ userId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/assignDelegateToCommittee",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, userId, committeeId } = await request.json();
    const assignmentId = await ctx.runMutation(internal.api.assignDelegateToCommittee, {
      eventId,
      userId,
      committeeId,
    });
    return new Response(JSON.stringify({ assignmentId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getAnnouncementsByEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId } = await request.json();
    const announcements = await ctx.runQuery(internal.api.getAnnouncementsByEvent, { eventId });
    return new Response(JSON.stringify(announcements), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/createAnnouncement",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, title, content, createdBy, isPinned } = await request.json();
    const args: any = { eventId, title, content, createdBy };
    if (isPinned !== null && isPinned !== undefined) args.isPinned = isPinned;
    const announcementId = await ctx.runMutation(internal.api.createAnnouncement, args);
    return new Response(JSON.stringify({ announcementId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getChatMessagesByEvent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId } = await request.json();
    const messages = await ctx.runQuery(internal.api.getChatMessagesByEvent, { eventId });
    return new Response(JSON.stringify(messages), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/sendChatMessage",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, senderId, message } = await request.json();
    const messageId = await ctx.runMutation(internal.api.sendChatMessage, {
      eventId,
      senderId,
      message,
    });
    return new Response(JSON.stringify({ messageId }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getAllUsers",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const users = await ctx.runQuery(internal.api.getAllUsers);
    return new Response(JSON.stringify(users), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getAllEvents",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const events = await ctx.runQuery(internal.api.getAllEvents);
    return new Response(JSON.stringify(events), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/getAllCommittees",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const committees = await ctx.runQuery(internal.api.getAllCommittees);
    return new Response(JSON.stringify(committees), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/updateEventPayment",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, stripeSessionId, stripePaymentIntentId, plan, expiresAt } = await request.json();
    await ctx.runMutation(internal.api.updateEventPayment, {
      eventId,
      stripeSessionId,
      stripePaymentIntentId,
      plan,
      expiresAt,
    });
    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

http.route({
  path: "/api/updateEventDelegateCount",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const { eventId, count } = await request.json();
    await ctx.runMutation(internal.api.updateEventDelegateCount, { eventId, count });
    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }),
});

export default http;
